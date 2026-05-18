#!/usr/bin/env python3
"""Method B Multi-Domain Benchmark v2 with LG Loader Fix"""

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
    for col in ['soc_target', 'soc_method_b', 'soc_method_b_soc_windowed']:
        if col in df.columns:
            return df[col]
    return None

domains = {}

# SP2
print("\nLoading SP2...")
try:
    df_sp2 = pd.read_parquet(ROOT / "data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet")
    df_sp2_clean = df_sp2[feature_cols + ['soc_method_b_sp']].dropna()
    df_sp2_clean = df_sp2_clean.rename(columns={'soc_method_b_sp': target_col})
    domains['SP2'] = df_sp2_clean.sample(min(40000, len(df_sp2_clean)), random_state=42).reset_index(drop=True)
    print(f"  OK: {len(domains['SP2'])} rows")
except Exception as e:
    print(f"  ERROR: {str(e)[:50]}")

# IoT
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
            print(f"  OK: {len(domains['IoT'])} rows")
except Exception as e:
    print(f"  ERROR: {str(e)[:50]}")

# LG
print("Loading LG...")
lg_path = ROOT / "data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet"

if lg_path.exists():
    try:
        dfs_lg = []
        part_files = sorted(lg_path.glob("part_*.parquet"))
        print(f"  Found {len(part_files)} part files")

        for i, part_file in enumerate(part_files[:50]):
            try:
                df_part = pd.read_parquet(part_file)
                dfs_lg.append(df_part)
            except:
                pass

        if dfs_lg:
            df_lg = pd.concat(dfs_lg, ignore_index=True)
            print(f"  Loaded {len(dfs_lg)} parts ({len(df_lg)} rows)")

            df_lg_norm = normalize_features(df_lg)
            if df_lg_norm is not None:
                y_lg = get_target(df_lg)
                if y_lg is not None:
                    if 'cell_id' in df_lg.columns:
                        ood_cells = {549, 562, 575, 582, 607, 551, 555, 593}
                        mask = ~df_lg['cell_id'].isin(ood_cells)
                        df_lg_norm = df_lg_norm[mask]
                        y_lg = y_lg[mask]

                    mask_valid = (y_lg >= 0) & (y_lg <= 1)
                    df_lg_norm = df_lg_norm[mask_valid]
                    y_lg = y_lg[mask_valid]

                    df_lg_clean = pd.concat([df_lg_norm, y_lg.rename(target_col)], axis=1)
                    df_lg_clean = df_lg_clean.dropna()

                    if len(df_lg_clean) > 0:
                        domains['LG'] = df_lg_clean.sample(min(40000, len(df_lg_clean)), random_state=42).reset_index(drop=True)
                        print(f"  OK: {len(domains['LG'])} rows")
    except Exception as e:
        print(f"  ERROR: {str(e)[:50]}")
else:
    print(f"  NOT FOUND: {lg_path}")

# Cross-domain benchmark
print(f"\nDomains: {sorted(domains.keys())}\n")
print("Ridge Cross-Domain Validation")
print("=" * 80)

metrics_md = []
status_md = []

for train_dom in sorted(domains.keys()):
    for test_dom in sorted(domains.keys()):
        if train_dom == test_dom:
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
                'R2': round(r2, 4),
                'MAE': round(mae, 4),
                'RMSE': round(rmse, 4),
                'train_rows': len(X_train),
                'test_rows': len(X_test)
            })
            status_md.append({'train': train_dom, 'test': test_dom, 'status': 'OK'})

            print(f"  {train_dom} -> {test_dom}: R2={r2:.4f}")

        except Exception as e:
            metrics_md.append({
                'train_domain': train_dom,
                'test_domain': test_dom,
                'R2': None,
                'MAE': None,
                'RMSE': None,
                'train_rows': -1,
                'test_rows': -1
            })
            status_md.append({'train': train_dom, 'test': test_dom, 'status': 'ERROR'})

# Save
pd.DataFrame(metrics_md).to_csv(ODIR / "method_b_multidomain_benchmark_metrics_v2.csv", index=False)
pd.DataFrame(status_md).to_csv(ODIR / "method_b_multidomain_benchmark_status_v2.csv", index=False)

print("\n[OK] Saved v2 files\n")
