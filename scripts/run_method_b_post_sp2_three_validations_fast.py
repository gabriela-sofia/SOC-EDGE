#!/usr/bin/env python3
"""
Method B Post-SP2 Three Validations (Ridge only, fast)
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT = Path("/sessions/eager-stoic-euler/mnt/SOC")
ODIR = ROOT / "outputs/external_datasets"

print("Method B Post-SP2 Three Validations (Ridge Diagnostic)")
print("=" * 80)

# Load SP2
print("\nLoading SP2...")
df_sp2 = pd.read_parquet(ROOT / "data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet")
feature_cols = ['voltage_V', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
target_col = 'soc_method_b_sp'

df_sp2 = df_sp2.dropna(subset=feature_cols + [target_col])
df_sp2['profile'] = df_sp2['profile_type'].str.strip() if 'profile_type' in df_sp2.columns else 'unknown'
df_sp2['temp'] = df_sp2['temperature_condition'].str.strip() if 'temperature_condition' in df_sp2.columns else 'unknown'

print(f"  Total: {len(df_sp2)} rows")
print(f"  Profiles: {sorted(df_sp2['profile'].unique())}")
print(f"  Temps: {sorted(df_sp2['temp'].unique())}")

# ============================================================================
# VALIDATION 1: SP2 LOPO
# ============================================================================
print("\n[1] SP2 LEAVE-ONE-PROFILE-OUT")
print("=" * 80)

metrics_lopo = []
for test_profile in sorted(df_sp2['profile'].unique()):
    train_idx = df_sp2['profile'] != test_profile
    test_idx = df_sp2['profile'] == test_profile

    X_train = df_sp2.loc[train_idx, feature_cols].copy()
    y_train = df_sp2.loc[train_idx, target_col].copy()
    X_test = df_sp2.loc[test_idx, feature_cols].copy()
    y_test = df_sp2.loc[test_idx, target_col].copy()

    if len(X_train) < 100 or len(X_test) < 100:
        print(f"  {test_profile}: SKIP")
        continue

    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_scaled, y_train)
    y_pred = ridge.predict(X_test_scaled)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    metrics_lopo.append({
        'validation_type': 'sp2_lopo',
        'fold': test_profile,
        'model': 'Ridge',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2, 4),
        'MAE': round(mae, 4),
        'RMSE': round(rmse, 4)
    })
    print(f"  {test_profile}: R²={r2:.4f}, MAE={mae:.4f}")

pd.DataFrame(metrics_lopo).to_csv(ODIR / "sp2_leave_one_profile_out_metrics.csv", index=False)
print(f"[OK] Saved: sp2_leave_one_profile_out_metrics.csv")

# ============================================================================
# VALIDATION 2: SP2 LOTO
# ============================================================================
print("\n[2] SP2 LEAVE-ONE-TEMPERATURE-OUT")
print("=" * 80)

metrics_loto = []
for test_temp in sorted(df_sp2['temp'].unique()):
    train_idx = df_sp2['temp'] != test_temp
    test_idx = df_sp2['temp'] == test_temp

    X_train = df_sp2.loc[train_idx, feature_cols].copy()
    y_train = df_sp2.loc[train_idx, target_col].copy()
    X_test = df_sp2.loc[test_idx, feature_cols].copy()
    y_test = df_sp2.loc[test_idx, target_col].copy()

    if len(X_train) < 100 or len(X_test) < 100:
        print(f"  {test_temp}: SKIP")
        continue

    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_scaled, y_train)
    y_pred = ridge.predict(X_test_scaled)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    metrics_loto.append({
        'validation_type': 'sp2_loto',
        'fold': test_temp,
        'model': 'Ridge',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2, 4),
        'MAE': round(mae, 4),
        'RMSE': round(rmse, 4)
    })
    print(f"  {test_temp}: R²={r2:.4f}, MAE={mae:.4f}")

pd.DataFrame(metrics_loto).to_csv(ODIR / "sp2_leave_one_temperature_out_metrics.csv", index=False)
print(f"[OK] Saved: sp2_leave_one_temperature_out_metrics.csv")

# ============================================================================
# VALIDATION 3: MULTI-DOMAIN BENCHMARK (sample-based)
# ============================================================================
print("\n[3] MULTI-DOMAIN BENCHMARK")
print("=" * 80)

domains = {}

# SP2
domains['SP2'] = df_sp2[feature_cols + [target_col]].sample(
    min(40000, len(df_sp2)), random_state=42).reset_index(drop=True)
print(f"  SP2: {len(domains['SP2'])} rows")

# IoT
try:
    df_iot = pd.read_parquet(ROOT / "outputs/external_datasets/iot_method_b_extracted.parquet")
    df_iot = df_iot.dropna(subset=feature_cols + ['soc_method_b_soc_windowed'])
    df_iot = df_iot.rename(columns={'soc_method_b_soc_windowed': target_col})
    domains['IoT'] = df_iot[feature_cols + [target_col]].reset_index(drop=True)
    print(f"  IoT: {len(domains['IoT'])} rows")
except:
    print(f"  IoT: NOT FOUND")

# LG
try:
    df_lg = pd.read_parquet(ROOT / "data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet")
    ood_cells = {549, 562, 575, 582, 607, 551, 555, 593}
    if 'cell_id' in df_lg.columns:
        df_lg = df_lg[~df_lg['cell_id'].isin(ood_cells)]
    df_lg = df_lg.dropna(subset=feature_cols + ['method_b_lg_recomputed'])
    df_lg = df_lg.rename(columns={'method_b_lg_recomputed': target_col})
    domains['LG'] = df_lg[feature_cols + [target_col]].sample(
        min(40000, len(df_lg)), random_state=42).reset_index(drop=True)
    print(f"  LG: {len(domains['LG'])} rows")
except:
    print(f"  LG: NOT FOUND")

# Oxford (optional)
try:
    candidates = [
        ROOT / "CORE/outputs/stage4c_final_results.parquet",
        ROOT / "CORE/stage4c_final_results/stage4c_final_results.parquet",
    ]
    for cand in candidates:
        if cand.exists():
            df_ox = pd.read_parquet(cand)
            if 'method_b_soc_q_cycle' in df_ox.columns:
                df_ox = df_ox.rename(columns={'method_b_soc_q_cycle': target_col})
            df_ox = df_ox.dropna(subset=feature_cols + [target_col])
            domains['Oxford'] = df_ox[feature_cols + [target_col]].sample(
                min(40000, len(df_ox)), random_state=42).reset_index(drop=True)
            print(f"  Oxford: {len(domains['Oxford'])} rows")
            break
except:
    pass

# Cross-domain matrix (Ridge only)
metrics_md = []
status_md = []

for train_dom in domains.keys():
    for test_dom in domains.keys():
        if train_dom == test_dom:
            status_md.append({'train': train_dom, 'test': test_dom, 'status': 'SKIP_SAME'})
            continue

        try:
            X_train = domains[train_dom][feature_cols]
            y_train = domains[train_dom][target_col]
            X_test = domains[test_dom][feature_cols]
            y_test = domains[test_dom][target_col]

            scaler = MinMaxScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            ridge = Ridge(alpha=1.0)
            ridge.fit(X_train_s, y_train)
            y_pred = ridge.predict(X_test_s)

            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))

            metrics_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'model': 'Ridge',
                'train_rows': len(X_train),
                'test_rows': len(X_test),
                'R2': round(r2, 4),
                'MAE': round(mae, 4),
                'RMSE': round(rmse, 4)
            })
            status_md.append({'train': train_dom, 'test': test_dom, 'status': 'OK'})
            print(f"  {train_dom} → {test_dom}: R²={r2:.4f}")

        except Exception as e:
            status_md.append({'train': train_dom, 'test': test_dom, 'status': f'ERROR'})

pd.DataFrame(metrics_md).to_csv(ODIR / "method_b_multidomain_benchmark_metrics.csv", index=False)
pd.DataFrame(status_md).to_csv(ODIR / "method_b_multidomain_benchmark_status.csv", index=False)
print(f"[OK] Saved: method_b_multidomain_benchmark_metrics.csv")

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)
