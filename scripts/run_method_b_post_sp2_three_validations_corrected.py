#!/usr/bin/env python3
"""
Method B Post-SP2 Three Validations (Corrected paths, Ridge only)
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

print("Method B Post-SP2 Three Validations (Corrected)")
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

# ============================================================================
# VALIDATION 1 & 2: SP2 LOPO + LOTO (already done, reload from CSV)
# ============================================================================
print("\n[1-2] SP2 LOPO + LOTO (using existing results)")
print("=" * 80)

lopo_df = pd.read_csv(ODIR / "sp2_leave_one_profile_out_metrics.csv")
loto_df = pd.read_csv(ODIR / "sp2_leave_one_temperature_out_metrics.csv")

print("LOPO Summary:")
print(f"  Mean R²: {lopo_df['R2'].mean():.4f} ± {lopo_df['R2'].std():.4f}")
print(f"  Best: {lopo_df.loc[lopo_df['R2'].idxmax(), 'fold']} ({lopo_df['R2'].max():.4f})")
print(f"  Worst: {lopo_df.loc[lopo_df['R2'].idxmin(), 'fold']} ({lopo_df['R2'].min():.4f})")

print("\nLOTO Summary:")
print(f"  Mean R²: {loto_df['R2'].mean():.4f} ± {loto_df['R2'].std():.4f}")
print(f"  Best: {loto_df.loc[loto_df['R2'].idxmax(), 'fold']} ({loto_df['R2'].max():.4f})")
print(f"  Worst: {loto_df.loc[loto_df['R2'].idxmin(), 'fold']} ({loto_df['R2'].min():.4f})")

# ============================================================================
# VALIDATION 3: MULTI-DOMAIN BENCHMARK (corrected paths)
# ============================================================================
print("\n[3] MULTI-DOMAIN BENCHMARK (corrected paths)")
print("=" * 80)

domains = {}

# SP2
domains['SP2'] = df_sp2[feature_cols + [target_col]].sample(
    min(40000, len(df_sp2)), random_state=42).reset_index(drop=True)
print(f"  SP2: {len(domains['SP2'])} rows")

# IoT
print("  Loading IoT...")
try:
    df_iot = pd.read_parquet(ODIR / "iot_method_b_extracted.parquet")
    print(f"    Found IoT parquet")

    # Check columns
    available_cols = [c for c in feature_cols if c in df_iot.columns]
    target_candidates = ['soc_method_b_soc_windowed', 'soc_method_b', 'method_b_soc']
    available_target = None
    for tc in target_candidates:
        if tc in df_iot.columns:
            available_target = tc
            break

    if len(available_cols) >= 5 and available_target:
        df_iot = df_iot.dropna(subset=available_cols + [available_target])
        df_iot_clean = df_iot[available_cols].copy()
        df_iot_clean[target_col] = df_iot[available_target]
        domains['IoT'] = df_iot_clean.reset_index(drop=True)
        print(f"    IoT loaded: {len(domains['IoT'])} rows")
    else:
        print(f"    IoT has {len(available_cols)}/5 features, target={available_target}")
except Exception as e:
    print(f"    Error: {str(e)[:60]}")

# LG (corrected path)
print("  Loading LG...")
try:
    lg_path = ROOT / "data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet"
    df_lg = pd.read_parquet(lg_path)
    print(f"    Found LG parquet")

    # Check columns
    available_cols = [c for c in feature_cols if c in df_lg.columns]
    target_candidates = ['method_b_lg_recomputed', 'soc_method_b', 'method_b']
    available_target = None
    for tc in target_candidates:
        if tc in df_lg.columns:
            available_target = tc
            break

    if len(available_cols) >= 5 and available_target:
        # Filter OOD cells
        ood_cells = {549, 562, 575, 582, 607, 551, 555, 593}
        if 'cell_id' in df_lg.columns:
            df_lg = df_lg[~df_lg['cell_id'].isin(ood_cells)]

        df_lg = df_lg.dropna(subset=available_cols + [available_target])
        df_lg_clean = df_lg[available_cols].copy()
        df_lg_clean[target_col] = df_lg[available_target]
        domains['LG'] = df_lg_clean.sample(min(40000, len(df_lg_clean)), random_state=42).reset_index(drop=True)
        print(f"    LG loaded: {len(domains['LG'])} rows")
    else:
        print(f"    LG has {len(available_cols)}/5 features, target={available_target}")
except Exception as e:
    print(f"    Error: {str(e)[:60]}")

print(f"\n  Domains ready: {list(domains.keys())}")

# Cross-domain matrix
metrics_md = []
status_md = []

for train_dom in sorted(domains.keys()):
    for test_dom in sorted(domains.keys()):
        if train_dom == test_dom:
            status_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'model': 'Ridge',
                'status': 'SKIP_SAME_DOMAIN'
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
                'RMSE': round(rmse, 4),
                'status': 'OK'
            })
            status_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'model': 'Ridge',
                'status': 'OK'
            })
            print(f"  {train_dom} → {test_dom}: R²={r2:.4f}")

        except Exception as e:
            print(f"  {train_dom} → {test_dom}: ERROR {str(e)[:30]}")
            metrics_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'model': 'Ridge',
                'train_rows': -1,
                'test_rows': -1,
                'R2': np.nan,
                'MAE': np.nan,
                'RMSE': np.nan,
                'status': f'ERROR'
            })
            status_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'model': 'Ridge',
                'status': f'ERROR'
            })

pd.DataFrame(metrics_md).to_csv(ODIR / "method_b_multidomain_benchmark_metrics.csv", index=False)
pd.DataFrame(status_md).to_csv(ODIR / "method_b_multidomain_benchmark_status.csv", index=False)
print(f"\n[OK] Multidomain benchmark saved")

# Summary
print("\n" + "=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)
print(f"\n1. SP2 LOPO: {len(lopo_df)} folds, Mean R²={lopo_df['R2'].mean():.4f}")
print(f"2. SP2 LOTO: {len(loto_df)} folds, Mean R²={loto_df['R2'].mean():.4f}")
print(f"3. Multi-domain: {len(metrics_md)} cross-domain pairs")

if len(metrics_md) > 0:
    md_ok = pd.DataFrame(metrics_md)
    md_ok = md_ok[md_ok['status'] == 'OK']
    if len(md_ok) > 0:
        print(f"   Successful: {len(md_ok)} pairs, Best R²={md_ok['R2'].max():.4f}")

print("\n[OK] All validations complete\n")
