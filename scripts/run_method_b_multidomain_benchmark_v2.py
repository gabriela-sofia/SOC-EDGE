#!/usr/bin/env python3
"""
Method B Multi-Domain Benchmark v2 (LG Loader Fix)
Runs Ridge cross-domain validation: IoT, SP2, LG (if loadable)
No Oxford (preprocessing undocumented).
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

print("Method B Multi-Domain Benchmark v2 (LG Loader Fix)")
print("=" * 80)

feature_cols = ['voltage_V', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
target_col = 'soc_method_b'

def normalize_features(df):
    """Map columns to feature contract"""
    normalized = df.copy()
    if 'voltage_v' in normalized.columns:
        normalized['voltage_V'] = normalized['voltage_v']
    elif 'voltage_V' not in normalized.columns:
        return None

    if 'current_ma' in normalized.columns:
        normalized['current_abs_A'] = normalized['current_ma'] / 1000.0
    elif 'current_abs_a' in normalized.columns:
        normalized['current_abs_A'] = normalized['current_abs_a']
    elif 'current_abs_A' not in normalized.columns:
        return None

    if 'temperature_c' in normalized.columns:
        normalized['temperature_C'] = normalized['temperature_c']
    elif 'temperature_C' not in normalized.columns:
        return None

    if 'delta_voltage' not in normalized.columns:
        normalized['delta_voltage'] = normalized['voltage_V'].diff().fillna(0)
    if 'delta_temperature' not in normalized.columns:
        normalized['delta_temperature'] = normalized['temperature_C'].diff().fillna(0)
    if 'delta_current' not in normalized.columns:
        normalized['delta_current'] = normalized['current_abs_A'].diff().fillna(0)

    return normalized[feature_cols]

def get_target(df):
    """Find Method B target column"""
    for col in ['soc_target', 'soc_method_b', 'soc_method_b_soc_windowed', 'method_b_lg_recomputed', 'method_b_soc', 'soc_method_b_sp']:
        if col in df.columns:
            return df[col]
    return None

domains = {}

# ============================================================================
# LOAD SP2
# ============================================================================
print("\nLoading SP2...")
try:
    df_sp2 = pd.read_parquet(ROOT / "data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet")
    df_sp2_clean = df_sp2[feature_cols + ['soc_method_b_sp']].dropna()
    df_sp2_clean = df_sp2_clean.rename(columns={'soc_method_b_sp': target_col})
    domains['SP2'] = df_sp2_clean.sample(min(40000, len(df_sp2_clean)), random_state=42).reset_index(drop=True)
    print(f"  ✓ SP2: {len(domains['SP2'])} rows")
except Exception as e:
    print(f"  ✗ SP2: {str(e)[:60]}")

# ============================================================================
# LOAD IoT
# ============================================================================
print("Loading IoT...")
try:
    df_iot = pd.read_parquet(ODIR / "iot_method_b_extracted.parquet")
    df_iot_norm = normalize_features(df_iot)
    if df_iot_norm is not None:
        y_iot = get_target(df_iot)
        if y_iot is not None:
            df_iot_clean = pd.concat([df_iot_norm, y_iot.rename(target_col)], axis=1)
            df_iot_clean = df_iot_clean.dropna()
            domains['IoT'] = df_iot_clean.reset_index(drop=True)
            print(f"  ✓ IoT: {len(domains['IoT'])} rows")
        else:
            print(f"  ✗ IoT: No target found")
    else:
        print(f"  ✗ IoT: Feature mapping failed")
except Exception as e:
    print(f"  ✗ IoT: {str(e)[:60]}")

# ============================================================================
# LOAD LG (with corrected path and recursive part file reading)
# ============================================================================
print("Loading LG...")
lg_path = ROOT / "data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet"
lg_alt_path = ROOT / "data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet"

if lg_path.exists():
    print(f"  Found LG parquet directory: {lg_path}")
    dfs_lg = []
    parts_dir = lg_path

    # Read all part_*.parquet files (including part_00000, part_00001, etc.)
    part_files = sorted(parts_dir.glob("part_*.parquet")) + sorted(parts_dir.glob("part_0*.parquet"))
    print(f"  Found {len(part_files)} part files")

    for part_file in part_files:
        try:
            df_part = pd.read_parquet(part_file)
            dfs_lg.append(df_part)
        except Exception as e:
            print(f"    Skipping {part_file.name}: {str(e)[:40]}")

    if dfs_lg:
        print(f"  Successfully loaded {len(dfs_lg)} parts")
        df_lg = pd.concat(dfs_lg, ignore_index=True)
        print(f"  Total rows from LG parts: {len(df_lg)}")

        try:
            # Normalize features
            df_lg_norm = normalize_features(df_lg)
            if df_lg_norm is not None:
                y_lg = get_target(df_lg)
                if y_lg is not None:
                    # Filter OOD cells
                    if 'cell_id' in df_lg.columns:
                        ood_cells = {549, 562, 575, 582, 607, 551, 555, 593}
                        mask = ~df_lg['cell_id'].isin(ood_cells)
                        df_lg_norm = df_lg_norm[mask]
                        y_lg = y_lg[mask]
                        print(f"  Filtered OOD cells: {(~mask).sum()} removed")

                    # Filter target range
                    y_lg = y_lg[mask] if 'mask' in locals() else y_lg
                    mask_valid_target = (y_lg >= 0) & (y_lg <= 1)
                    df_lg_norm = df_lg_norm[mask_valid_target]
                    y_lg = y_lg[mask_valid_target]

                    # Build dataframe
                    df_lg_clean = pd.concat([df_lg_norm, y_lg.rename(target_col)], axis=1)
                    df_lg_clean = df_lg_clean.dropna()

                    if len(df_lg_clean) > 0:
                        domains['LG'] = df_lg_clean.sample(min(40000, len(df_lg_clean)), random_state=42).reset_index(drop=True)
                        print(f"  ✓ LG: {len(domains['LG'])} rows (after filtering)")
                    else:
                        print(f"  ✗ LG: No valid rows after filtering")
                else:
                    print(f"  ✗ LG: No target found")
            else:
                print(f"  ✗ LG: Feature mapping failed")
        except Exception as e:
            print(f"  ✗ LG processing: {str(e)[:60]}")
    else:
        print(f"  ✗ LG: Could not load any part files")
else:
    print(f"  ✗ LG path not found: {lg_path}")

# ============================================================================
# MULTI-DOMAIN CROSS-VALIDATION
# ============================================================================
print(f"\nDomains ready: {sorted(domains.keys())}")
print("\nRunning Ridge cross-domain validation...")
print("=" * 80)

metrics_md = []
status_md = []

for train_dom in sorted(domains.keys()):
    for test_dom in sorted(domains.keys()):
        if train_dom == test_dom:
            status_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
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
                'RMSE': round(rmse, 4)
            })
            status_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'status': 'OK'
            })

            # Interpret result
            if r2 > 0.5:
                result_str = f"Transferable"
            elif r2 > 0:
                result_str = f"Weak transfer"
            else:
                result_str = f"Domain shift"

            print(f"  {train_dom:6s} → {test_dom:6s}: R²={r2:8.4f} ({result_str})")

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
                'status': f'ERROR'
            })
            print(f"  {train_dom:6s} → {test_dom:6s}: ERROR")

# ============================================================================
# SAVE RESULTS
# ============================================================================
pd.DataFrame(metrics_md).to_csv(ODIR / "method_b_multidomain_benchmark_metrics_v2.csv", index=False)
pd.DataFrame(status_md).to_csv(ODIR / "method_b_multidomain_benchmark_status_v2.csv", index=False)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"\nDomains loaded: {len(domains)}")
for dom, df in domains.items():
    print(f"  {dom}: {len(df)} rows")

if len(metrics_md) > 0:
    md_ok = [m for m in metrics_md if m['R2'] is not None]
    if md_ok:
        r2_vals = [m['R2'] for m in md_ok]
        print(f"\nCross-domain pairs: {len(md_ok)}")
        print(f"  Best R²: {max(r2_vals):.4f}")
        print(f"  Worst R²: {min(r2_vals):.4f}")

print(f"\nFiles saved:")
print(f"  method_b_multidomain_benchmark_metrics_v2.csv")
print(f"  method_b_multidomain_benchmark_status_v2.csv")
print("\n[OK] Complete\n")
