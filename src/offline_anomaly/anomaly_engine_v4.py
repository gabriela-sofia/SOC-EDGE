"""
Offline Anomaly Residual Engine — V4
Projeto: SOC/SOH/anomalias para baterias em IoT/Edge AI/TinyML com ESP32
Date: 2026-05-13
NAO e TCC.

STATUS: OFFLINE EXPERIMENTAL — NOT validated for real sensor deployment.
Thresholds are statistical (from normal base) or physics-aware (from LG 18650 spec).
All threshold origins documented in anomaly_config_v4.json.

Rule types:
  PHYSICAL      — hard limits from battery spec
  RESIDUAL      — statistical deviation from model predictions
  THERMAL       — temperature/thermal dynamics
  DEGRADATION   — SOH-based degradation detection
  DOMAIN_SHIFT  — cross-dataset distribution mismatch
  TEMPORAL      — time-series consistency
  HEURISTIC     — expert rule without formal derivation (marked explicitly)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------
# 1. Signal delta computation
# ---------------------------------------------------------------

def compute_signal_deltas(df: pd.DataFrame,
                          signal_cols: List[str],
                          time_col: Optional[str] = None) -> pd.DataFrame:
    """
    Compute first-order differences for each signal column.
    Returns df with new delta_<col> columns.
    Boundary samples (first of each cycle) are set to 0.
    """
    df = df.copy()
    for col in signal_cols:
        if col in df.columns:
            delta_col = f"delta_{col}"
            if delta_col not in df.columns:
                df[delta_col] = df[col].diff().fillna(0)
    return df


# ---------------------------------------------------------------
# 2. Residual computation
# ---------------------------------------------------------------

def compute_soc_residual(df: pd.DataFrame,
                         soc_actual_col: str = "soc_method_b",
                         soc_pred_col: str = "soc_prediction") -> pd.DataFrame:
    """
    SOC residual = actual SOC - predicted SOC.
    Positive: model underestimates (cell appears more charged than model expects).
    Negative: model overestimates.
    Sets soc_residual = NaN if prediction is unavailable.
    """
    df = df.copy()
    if soc_actual_col in df.columns and soc_pred_col in df.columns:
        has_pred = df[soc_pred_col].notna()
        df["soc_residual"] = np.where(
            has_pred,
            df[soc_actual_col] - df[soc_pred_col],
            np.nan,
        )
    else:
        df["soc_residual"] = np.nan
    return df


def compute_soh_residual(df: pd.DataFrame,
                         soh_actual_col: str = "soh_target",
                         soh_pred_col: str = "soh_prediction") -> pd.DataFrame:
    """
    SOH residual = actual SOH - predicted SOH.
    Large negative residual: faster-than-expected degradation.
    """
    df = df.copy()
    if soh_actual_col in df.columns and soh_pred_col in df.columns:
        has_pred = df[soh_pred_col].notna()
        df["soh_residual"] = np.where(
            has_pred,
            df[soh_actual_col] - df[soh_pred_col],
            np.nan,
        )
    else:
        df["soh_residual"] = np.nan
    return df


# ---------------------------------------------------------------
# 3. Degradation rate
# ---------------------------------------------------------------

def compute_degradation_rate(df: pd.DataFrame,
                              soh_col: str = "soh_target",
                              cycle_col: str = "cycle_id") -> pd.DataFrame:
    """
    Degradation rate = -delta(SOH) / delta(cycle).
    Positive = degradation (SOH decreasing).
    Computed per (cell_id, cycle_id) if available.
    Returns df with degradation_rate column.
    Requires at least 2 SOH points per cell.
    """
    df = df.copy()
    df["degradation_rate"] = np.nan

    if soh_col not in df.columns or cycle_col not in df.columns:
        return df

    group_col = "cell_id" if "cell_id" in df.columns else None

    # Ensure cycle_col is numeric for diff()
    df = df.copy()
    try:
        df[cycle_col] = pd.to_numeric(df[cycle_col], errors="coerce")
    except Exception:
        pass

    if group_col:
        for cell, grp in df.groupby(group_col):
            grp_sorted = grp.drop_duplicates(subset=[cycle_col]).sort_values(cycle_col)
            if len(grp_sorted) < 2:
                continue
            delta_soh   = grp_sorted[soh_col].diff()
            delta_cycle = grp_sorted[cycle_col].diff().replace(0, np.nan)
            rate = (-delta_soh / delta_cycle).fillna(0)
            df.loc[grp_sorted.index, "degradation_rate"] = rate.values
    else:
        grp_sorted = df.sort_values(cycle_col)
        delta_soh   = grp_sorted[soh_col].diff()
        delta_cycle = grp_sorted[cycle_col].diff().replace(0, np.nan)
        df.loc[grp_sorted.index, "degradation_rate"] = (-delta_soh / delta_cycle).fillna(0).values

    return df


# ---------------------------------------------------------------
# 4. Domain shift score
# ---------------------------------------------------------------

def compute_domain_shift_score(df: pd.DataFrame,
                                reference_stats: Dict[str, Dict[str, float]],
                                feature_cols: List[str]) -> pd.DataFrame:
    """
    Domain shift score: mean normalized z-score across features.
    reference_stats: {feature: {"mean": float, "std": float}}
    Score = mean(|z_i|) where z_i = (x_i - ref_mean_i) / ref_std_i
    Severity: LOW < 1, MEDIUM < 2, HIGH < 3, SEVERE >= 3
    """
    df = df.copy()
    z_scores = []
    for col in feature_cols:
        if col in df.columns and col in reference_stats:
            mu  = reference_stats[col]["mean"]
            sig = reference_stats[col].get("std", 1.0)
            if sig <= 0:
                sig = 1.0
            z = (df[col] - mu).abs() / sig
            z_scores.append(z)

    if z_scores:
        df["domain_shift_score"] = pd.concat(z_scores, axis=1).mean(axis=1)
    else:
        df["domain_shift_score"] = 0.0
    return df


# ---------------------------------------------------------------
# 5. Physical range anomaly detection
# ---------------------------------------------------------------

def detect_physical_range_anomaly(df: pd.DataFrame,
                                   config: Dict) -> pd.DataFrame:
    """
    PHYSICAL rules — hard limits from LG 18650 spec.
    Flags: flag_voltage_range, flag_current_range, flag_temp_range
    origin: PHYSICS_AWARE (LG 18650 / IEC 61960 spec)
    """
    df = df.copy()
    v_lo  = config.get("voltage_min_V", 2.5)
    v_hi  = config.get("voltage_max_V", 4.25)
    t_lo  = config.get("temp_min_C", -20.0)
    t_hi  = config.get("temp_max_C", 60.0)
    i_hi  = config.get("current_max_A", 20.0)

    if "voltage_v" in df.columns:
        df["flag_voltage_range"] = (
            (df["voltage_v"] < v_lo) | (df["voltage_v"] > v_hi)
        ).astype(int)
    elif "voltage_V" in df.columns:
        df["flag_voltage_range"] = (
            (df["voltage_V"] < v_lo) | (df["voltage_V"] > v_hi)
        ).astype(int)
    else:
        df["flag_voltage_range"] = 0

    if "temperature_c" in df.columns:
        df["flag_temp_range"] = (
            (df["temperature_c"] < t_lo) | (df["temperature_c"] > t_hi)
        ).astype(int)
    elif "temperature_C" in df.columns:
        df["flag_temp_range"] = (
            (df["temperature_C"] < t_lo) | (df["temperature_C"] > t_hi)
        ).astype(int)
    else:
        df["flag_temp_range"] = 0

    for cur_col in ("current_abs_a", "current_abs_A", "current_abs"):
        if cur_col in df.columns:
            df["flag_current_range"] = (df[cur_col].abs() > i_hi).astype(int)
            break
    else:
        df["flag_current_range"] = 0

    return df


# ---------------------------------------------------------------
# 6. Abrupt deviation detection
# ---------------------------------------------------------------

def detect_abrupt_deviation(df: pd.DataFrame,
                             config: Dict) -> pd.DataFrame:
    """
    HEURISTIC — delta thresholds from training distribution (mean + k*std).
    Flags: flag_abrupt_voltage, flag_abrupt_current, flag_abrupt_temp
    threshold_origin: STATISTICAL_PERCENTILE_95 from normal base
    """
    df = df.copy()

    for (delta_col, flag_col, threshold_key) in [
        ("delta_voltage_V", "flag_abrupt_voltage", "delta_voltage_threshold"),
        ("delta_voltage_v", "flag_abrupt_voltage", "delta_voltage_threshold"),
        ("delta_current_abs_A", "flag_abrupt_current", "delta_current_threshold"),
        ("delta_temperature_C", "flag_abrupt_temp", "delta_temp_threshold"),
        ("delta_temperature_c", "flag_abrupt_temp", "delta_temp_threshold"),
    ]:
        if delta_col in df.columns and threshold_key in config:
            thr = config[threshold_key]
            flag = flag_col
            if flag not in df.columns:
                df[flag] = (df[delta_col].abs() > thr).astype(int)
            else:
                df[flag] = df[flag] | (df[delta_col].abs() > thr).astype(int)

    for f in ("flag_abrupt_voltage", "flag_abrupt_current", "flag_abrupt_temp"):
        if f not in df.columns:
            df[f] = 0

    return df


# ---------------------------------------------------------------
# 7. SOC temporal inconsistency
# ---------------------------------------------------------------

def detect_soc_temporal_inconsistency(df: pd.DataFrame,
                                       config: Dict) -> pd.DataFrame:
    """
    TEMPORAL — SOC jump between consecutive samples is physically impossible.
    A SOC jump > max_soc_jump_per_sample is flagged.
    threshold_origin: PHYSICS_AWARE (max charge rate 1C = 1 SOC unit / 3600s; 1s samples → 0.001/s typical)
    """
    df = df.copy()
    thr = config.get("max_soc_jump_per_sample", 0.05)
    soc_col = None
    for c in ("soc_method_b", "soc_v"):
        if c in df.columns:
            soc_col = c
            break

    if soc_col:
        delta_soc = df[soc_col].diff().abs().fillna(0)
        df["flag_soc_temporal"] = (delta_soc > thr).astype(int)
    else:
        df["flag_soc_temporal"] = 0

    return df


# ---------------------------------------------------------------
# 8. SOC prediction divergence
# ---------------------------------------------------------------

def detect_soc_prediction_divergence(df: pd.DataFrame,
                                      config: Dict) -> pd.DataFrame:
    """
    RESIDUAL — |soc_residual| > threshold signals model divergence.
    threshold_origin: STATISTICAL (95th percentile of residuals in normal base)
    """
    df = df.copy()
    thr = config.get("soc_residual_threshold", 0.1)

    if "soc_residual" in df.columns:
        df["flag_soc_divergence"] = (
            df["soc_residual"].abs().fillna(0) > thr
        ).astype(int)
    else:
        df["flag_soc_divergence"] = 0

    return df


# ---------------------------------------------------------------
# 9. SOH residual anomaly
# ---------------------------------------------------------------

def detect_soh_residual_anomaly(df: pd.DataFrame,
                                 config: Dict) -> pd.DataFrame:
    """
    DEGRADATION/RESIDUAL — unexpected SOH drop vs model prediction.
    Large negative soh_residual = faster degradation than expected.
    threshold_origin: STATISTICAL (5th percentile of SOH residuals in normal base)
    """
    df = df.copy()
    thr = config.get("soh_residual_threshold_neg", -0.1)

    if "soh_residual" in df.columns:
        df["flag_soh_residual"] = (
            df["soh_residual"].fillna(0) < thr
        ).astype(int)
    else:
        df["flag_soh_residual"] = 0

    return df


# ---------------------------------------------------------------
# 10. SOC/SOH consistency check
# ---------------------------------------------------------------

def detect_soc_soh_inconsistency(df: pd.DataFrame,
                                  config: Dict) -> pd.DataFrame:
    """
    RESIDUAL — when SOH is very low, high SOC is physically suspicious.
    Rule: if soh_target < soh_low_threshold AND soc_method_b > soc_high_threshold
    → INCONSISTENCY (likely sensor or estimation error).
    threshold_origin: HEURISTIC (no formal derivation)
    """
    df = df.copy()
    soh_thr = config.get("soc_soh_inconsistency_soh_threshold", 0.6)
    soc_thr = config.get("soc_soh_inconsistency_soc_threshold", 0.95)

    soh_col = "soh_target" if "soh_target" in df.columns else None
    soc_col = "soc_method_b" if "soc_method_b" in df.columns else None

    if soh_col and soc_col:
        low_soh = df[soh_col].fillna(1.0) < soh_thr
        high_soc = df[soc_col].fillna(0.0) > soc_thr
        df["flag_soc_soh_inconsistency"] = (low_soh & high_soc).astype(int)
    else:
        df["flag_soc_soh_inconsistency"] = 0

    return df


# ---------------------------------------------------------------
# 11. Degradation transition detection
# ---------------------------------------------------------------

def detect_degradation_transition(df: pd.DataFrame,
                                   config: Dict) -> pd.DataFrame:
    """
    DEGRADATION — flags when degradation_rate exceeds fast-degradation threshold.
    High degradation rate: cell approaching end-of-life or abnormal aging.
    threshold_origin: STATISTICAL from PoliMi degradation profile (95th percentile rate)
    """
    df = df.copy()
    thr = config.get("degradation_rate_threshold", 0.002)

    if "degradation_rate" in df.columns:
        df["flag_degradation_transition"] = (
            df["degradation_rate"].abs().fillna(0) > thr
        ).astype(int)
    else:
        df["flag_degradation_transition"] = 0

    return df


# ---------------------------------------------------------------
# 12. Thermal risk detection
# ---------------------------------------------------------------

def detect_thermal_risk(df: pd.DataFrame,
                         config: Dict) -> pd.DataFrame:
    """
    THERMAL — thermal runaway proxy.
    Rule: delta_temperature > thermal_delta_threshold AND current_abs > current_thermal_threshold.
    threshold_origin: HEURISTIC (thermal runaway precursor studies, not calibrated on real data)
    """
    df = df.copy()
    dt_thr = config.get("thermal_delta_threshold_C", 2.0)
    i_thr  = config.get("thermal_current_threshold_A", 3.0)

    dt_col = None
    for c in ("delta_temperature_C", "delta_temperature_c"):
        if c in df.columns:
            dt_col = c
            break

    ic_col = None
    for c in ("current_abs_a", "current_abs_A", "current_abs"):
        if c in df.columns:
            ic_col = c
            break

    if dt_col and ic_col:
        high_dt = df[dt_col].abs() > dt_thr
        high_i  = df[ic_col].abs() > i_thr
        df["flag_thermal_risk"] = (high_dt & high_i).astype(int)
    elif dt_col:
        df["flag_thermal_risk"] = (df[dt_col].abs() > dt_thr * 2).astype(int)
    else:
        df["flag_thermal_risk"] = 0

    return df


# ---------------------------------------------------------------
# 13. Domain shift flag
# ---------------------------------------------------------------

def detect_domain_shift_flag(df: pd.DataFrame,
                               config: Dict) -> pd.DataFrame:
    """
    DOMAIN_SHIFT — flags samples with high domain shift score.
    Not a true anomaly detector — warns that the model may be unreliable.
    threshold_origin: STATISTICAL (95th percentile of in-distribution shift scores)
    """
    df = df.copy()
    thr = config.get("domain_shift_score_threshold", 2.0)

    if "domain_shift_score" in df.columns:
        df["flag_domain_shift"] = (
            df["domain_shift_score"].fillna(0) > thr
        ).astype(int)
    else:
        df["flag_domain_shift"] = 0

    return df


# ---------------------------------------------------------------
# 14. Composite anomaly score
# ---------------------------------------------------------------

FLAG_WEIGHTS = {
    "flag_voltage_range":          3.0,   # PHYSICAL — hard limit
    "flag_current_range":          2.0,   # PHYSICAL
    "flag_temp_range":             2.0,   # PHYSICAL
    "flag_abrupt_voltage":         1.5,   # HEURISTIC
    "flag_abrupt_current":         1.0,   # HEURISTIC
    "flag_abrupt_temp":            1.0,   # HEURISTIC
    "flag_soc_temporal":           2.0,   # TEMPORAL
    "flag_soc_divergence":         1.5,   # RESIDUAL
    "flag_soh_residual":           2.0,   # DEGRADATION
    "flag_soc_soh_inconsistency":  2.5,   # RESIDUAL/HEURISTIC
    "flag_degradation_transition": 1.5,   # DEGRADATION
    "flag_thermal_risk":           3.0,   # THERMAL
    "flag_domain_shift":           0.5,   # DOMAIN_SHIFT (warning, not anomaly)
}

def compute_anomaly_score(df: pd.DataFrame,
                           weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """
    Weighted sum of all anomaly flags.
    Score = sum(w_i * flag_i) for all present flags.
    Normalized to [0, max_possible] (not 0-1: intentional — severity matters).
    """
    df = df.copy()
    w = weights or FLAG_WEIGHTS
    score = pd.Series(0.0, index=df.index)
    for flag_col, weight in w.items():
        if flag_col in df.columns:
            score += df[flag_col].fillna(0).astype(float) * weight
    df["anomaly_score"] = score.round(4)
    return df


def classify_anomaly_status(df: pd.DataFrame,
                              config: Dict) -> pd.DataFrame:
    """
    Classify anomaly_score into severity levels.
    NORMAL | WARNING | ANOMALY | CRITICAL
    Thresholds from config: score_warning, score_anomaly, score_critical
    """
    df = df.copy()
    s_warn = config.get("score_warning",  1.0)
    s_anom = config.get("score_anomaly",  3.0)
    s_crit = config.get("score_critical", 5.0)

    def classify(s):
        if s >= s_crit:
            return "CRITICAL"
        elif s >= s_anom:
            return "ANOMALY"
        elif s >= s_warn:
            return "WARNING"
        return "NORMAL"

    if "anomaly_score" in df.columns:
        df["anomaly_status"] = df["anomaly_score"].apply(classify)
    else:
        df["anomaly_status"] = "NORMAL"

    return df


# ---------------------------------------------------------------
# 15. Full pipeline runner (convenience)
# ---------------------------------------------------------------

def run_full_detection(df: pd.DataFrame,
                        config: Dict,
                        reference_stats: Optional[Dict] = None,
                        signal_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Run all detection steps in sequence.
    Returns df with all flag and score columns.
    """
    if signal_cols is None:
        signal_cols = ["voltage_V", "temperature_C", "current_abs_A",
                       "voltage_v", "temperature_c", "current_abs_a"]

    df = compute_signal_deltas(df, signal_cols)
    df = compute_soc_residual(df)
    df = compute_soh_residual(df)
    df = compute_degradation_rate(df)

    if reference_stats:
        feat_cols = [c for c in signal_cols if c in df.columns]
        df = compute_domain_shift_score(df, reference_stats, feat_cols)

    df = detect_physical_range_anomaly(df, config)
    df = detect_abrupt_deviation(df, config)
    df = detect_soc_temporal_inconsistency(df, config)
    df = detect_soc_prediction_divergence(df, config)
    df = detect_soh_residual_anomaly(df, config)
    df = detect_soc_soh_inconsistency(df, config)
    df = detect_degradation_transition(df, config)
    df = detect_thermal_risk(df, config)
    df = detect_domain_shift_flag(df, config)
    df = compute_anomaly_score(df)
    df = classify_anomaly_status(df, config)

    return df
