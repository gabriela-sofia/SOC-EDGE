#!/usr/bin/env python3
"""
Method B Post-SP2 Three Validations (Final, with column mapping)
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[1]
ODIR = ROOT / "outputs/external_datasets"

print("Method B Post-SP2 Three Validations (Final)")
print("=" * 80)

# Feature contract (target names)
feature_cols = ['voltage_V', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
target_col = 'soc_method_b'

def normalize_features(df):
    """Convert input columns to feature contract"""
    normalized = df.copy()

    # Voltage mapping
    if 'voltage_v' in normalized.columns:
        normalized['voltage_V'] = normalized['voltage_v']
    elif 'voltage_V' not in normalized.columns:
        return None

    # Current mapping (convert mA -> A if needed)
    if 'current_ma' in normalized.columns:
        normalized['current_abs_A'] = normalized['current_ma'] / 1000.0
    elif 'current_abs_a' in normalized.columns:
        normalized['current_abs_A'] = normalized['current_abs_a']
    elif 'current_abs_A' not in normalized.columns:
        return None

    # Temperature mapping
    if 'temperature_c' in normalized.columns:
        normalized['temperature_C'] = normalized['temperature_c']
    elif 'temperature_C' not in normalized.columns:
        return None

    # Compute deltas (simple differencing)
    if 'delta_voltage' not in normalized.columns:
        normalized['delta_voltage'] = normalized['voltage_V'].diff().fillna(0)
    if 'delta_temperature' not in normalized.columns:
        normalized['delta_temperature'] = normalized['temperature_C'].diff().fillna(0)
    if 'delta_current' not in normalized.columns:
        normalized['delta_current'] = normalized['current_abs_A'].diff().fillna(0)

    return normalized[feature_cols]

def get_target(df):
    """Extract Method B target from dataset"""
    for col in ['soc_method_b', 'soc_method_b_soc_windowed', 'method_b_lg_recomputed', 'method_b_soc', 'soc_method_b_sp']:
        if col in df.columns:
            return df[col]
    return None

# Load SP2
print("\nLoading SP2...")
df_sp2 = pd.read_parquet(ROOT / "data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet")
df_sp2['profile'] = df_sp2['profile_type'].str.strip() if 'profile_type' in df_sp2.columns else 'unknown'
df_sp2['temp'] = df_sp2['temperature_condition'].str.strip() if 'temperature_condition' in df_sp2.columns else 'unknown'

# Get SP2 metrics (already computed)
print("\n[1-2] SP2 LOPO + LOTO")
print("=" * 80)

lopo_df = pd.read_csv(ODIR / "sp2_leave_one_profile_out_metrics.csv")
loto_df = pd.read_csv(ODIR / "sp2_leave_one_temperature_out_metrics.csv")

print("Leave-One-Profile-Out (BJDST, DST, FUDS, US06):")
print(f"  Ridge mean R²: {lopo_df['R2'].mean():.4f} ± {lopo_df['R2'].std():.4f}")
print(f"  Ridge mean MAE: {lopo_df['MAE'].mean():.4f}")
for _, row in lopo_df.iterrows():
    print(f"    {row['fold']}: R²={row['R2']:.4f}, MAE={row['MAE']:.4f}")

print("\nLeave-One-Temperature-Out (0C, 25C, 45C):")
print(f"  Ridge mean R²: {loto_df['R2'].mean():.4f} ± {loto_df['R2'].std():.4f}")
print(f"  Ridge mean MAE: {loto_df['MAE'].mean():.4f}")
for _, row in loto_df.iterrows():
    print(f"    {row['fold']}: R²={row['R2']:.4f}, MAE={row['MAE']:.4f}")

# ============================================================================
# VALIDATION 3: MULTI-DOMAIN BENCHMARK (with corrected feature mapping)
# ============================================================================
print("\n[3] MULTI-DOMAIN BENCHMARK")
print("=" * 80)

domains = {}

# SP2
print("  Loading SP2...")
df_sp2_clean = df_sp2[feature_cols + ['soc_method_b_sp']].dropna()
df_sp2_clean = df_sp2_clean.rename(columns={'soc_method_b_sp': target_col})
domains['SP2'] = df_sp2_clean.sample(min(40000, len(df_sp2_clean)), random_state=42).reset_index(drop=True)
print(f"    SP2: {len(domains['SP2'])} rows")

# IoT (with feature mapping)
print("  Loading IoT...")
try:
    df_iot = pd.read_parquet(ODIR / "iot_method_b_extracted.parquet")
    df_iot_norm = normalize_features(df_iot)
    if df_iot_norm is not None:
        y_iot = get_target(df_iot)
        if y_iot is not None:
            df_iot_clean = pd.concat([df_iot_norm, y_iot.rename(target_col)], axis=1)
            df_iot_clean = df_iot_clean.dropna()
            domains['IoT'] = df_iot_clean.reset_index(drop=True)
            print(f"    IoT: {len(domains['IoT'])} rows")
        else:
            print(f"    IoT: No target column found")
    else:
        print(f"    IoT: Feature mapping failed")
except Exception as e:
    print(f"    IoT: Error {str(e)[:60]}")

# LG (with feature mapping)
print("  Loading LG...")
try:
    df_lg = pd.read_parquet(ROOT / "data/processed/external/lg18650_hg2/lg18650_hg2_method_b.parquet")
    df_lg_norm = normalize_features(df_lg)
    if df_lg_norm is not None:
        y_lg = get_target(df_lg)
        if y_lg is not None:
            # Filter OOD cells if available
            if 'cell_id' in df_lg.columns:
                ood_cells = {549, 562, 575, 582, 607, 551, 555, 593}
                mask = ~df_lg['cell_id'].isin(ood_cells)
                df_lg_norm = df_lg_norm[mask]
                y_lg = y_lg[mask]

            df_lg_clean = pd.concat([df_lg_norm, y_lg.rename(target_col)], axis=1)
            df_lg_clean = df_lg_clean.dropna()
            domains['LG'] = df_lg_clean.sample(min(40000, len(df_lg_clean)), random_state=42).reset_index(drop=True)
            print(f"    LG: {len(domains['LG'])} rows")
        else:
            print(f"    LG: No target column found")
    else:
        print(f"    LG: Feature mapping failed")
except Exception as e:
    print(f"    LG: Error {str(e)[:60]}")

print(f"\n  Domains available: {sorted(domains.keys())}")

# Cross-domain validation matrix
metrics_md = []
status_md = []

for train_dom in sorted(domains.keys()):
    for test_dom in sorted(domains.keys()):
        if train_dom == test_dom:
            status_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'model': 'Ridge',
                'status': 'SKIP'
            })
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
            status_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'status': 'OK'
            })
            print(f"    {train_dom} → {test_dom}: R²={r2:.4f}")

        except Exception as e:
            metrics_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'model': 'Ridge',
                'train_rows': -1,
                'test_rows': -1,
                'R2': None,
                'MAE': None,
                'RMSE': None
            })
            status_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'status': 'ERROR'
            })
            print(f"    {train_dom} → {test_dom}: ERROR")

# Save results
pd.DataFrame(metrics_md).to_csv(ODIR / "method_b_multidomain_benchmark_metrics.csv", index=False)
pd.DataFrame(status_md).to_csv(ODIR / "method_b_multidomain_benchmark_status.csv", index=False)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"\n1. SP2 Leave-One-Profile-Out: {len(lopo_df)} folds")
print(f"   Mean R²: {lopo_df['R2'].mean():.4f} ± {lopo_df['R2'].std():.4f}")

print(f"\n2. SP2 Leave-One-Temperature-Out: {len(loto_df)} folds")
print(f"   Mean R²: {loto_df['R2'].mean():.4f} ± {loto_df['R2'].std():.4f}")

print(f"\n3. Multi-Domain Benchmark: {len(domains)} domains")
if len(metrics_md) > 0:
    md_ok = [m for m in metrics_md if m['R2'] is not None]
    if md_ok:
        r2_vals = [m['R2'] for m in md_ok]
        print(f"   {len(md_ok)} cross-domain pairs")
        print(f"   Best R²: {max(r2_vals):.4f}")
        print(f"   Worst R²: {min(r2_vals):.4f}")

print(f"\n[OK] Results saved to outputs/external_datasets/\n")
