#!/usr/bin/env python3
"""
Method B Post-SP2 Three Validations
====================================
1. SP2 Leave-One-Profile-Out (cross-profile transfer)
2. SP2 Leave-One-Temperature-Out (thermal transfer)
3. Multi-Domain Benchmark (Oxford + LG + IoT + SP2)

Scientific validation only; no production models saved.
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT = Path("/sessions/eager-stoic-euler/mnt/SOC")
ODIR = ROOT / "outputs/external_datasets"
MDIR = ROOT / "models_external"
ODIR.mkdir(parents=True, exist_ok=True)
MDIR.mkdir(parents=True, exist_ok=True)

print("Method B Post-SP2 Three Validations")
print("=" * 80)

# ============================================================================
# VALIDATION 1: SP2 LEAVE-ONE-PROFILE-OUT (LOPO)
# ============================================================================
print("\n[1] SP2 LEAVE-ONE-PROFILE-OUT CROSS-VALIDATION")
print("=" * 80)

df_sp2 = pd.read_parquet(ROOT / "data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet")

feature_cols = ['voltage_V', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
target_col = 'soc_method_b_sp'

df_sp2 = df_sp2.dropna(subset=feature_cols + [target_col])
df_sp2['profile'] = df_sp2['profile_type'].str.strip() if 'profile_type' in df_sp2.columns else 'unknown'
profiles = df_sp2['profile'].unique()

print(f"Total rows: {len(df_sp2)}")
print(f"Profiles: {sorted(profiles)}")

metrics_lopo = []
for test_profile in sorted(profiles):
    train_idx = df_sp2['profile'] != test_profile
    test_idx = df_sp2['profile'] == test_profile

    X_train = df_sp2.loc[train_idx, feature_cols].copy()
    y_train = df_sp2.loc[train_idx, target_col].copy()
    X_test = df_sp2.loc[test_idx, feature_cols].copy()
    y_test = df_sp2.loc[test_idx, target_col].copy()

    if len(X_train) < 100 or len(X_test) < 100:
        print(f"  {test_profile}: SKIP (insufficient data)")
        continue

    # Ridge
    scaler_ridge = MinMaxScaler()
    X_train_scaled = scaler_ridge.fit_transform(X_train)
    X_test_scaled = scaler_ridge.transform(X_test)

    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_scaled, y_train)
    y_pred_ridge = ridge.predict(X_test_scaled)

    r2_ridge = r2_score(y_test, y_pred_ridge)
    mae_ridge = mean_absolute_error(y_test, y_pred_ridge)
    rmse_ridge = np.sqrt(mean_squared_error(y_test, y_pred_ridge))
    bias_ridge = np.mean(y_pred_ridge - y_test)
    oob_ridge = np.mean((y_pred_ridge < 0) | (y_pred_ridge > 1))

    metrics_lopo.append({
        'validation_type': 'sp2_lopo',
        'fold': test_profile,
        'model': 'Ridge',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2_ridge, 4),
        'MAE': round(mae_ridge, 4),
        'RMSE': round(rmse_ridge, 4),
        'bias': round(bias_ridge, 4),
        'oob_rate': round(oob_ridge, 4)
    })

    # MLP
    scaler_mlp = MinMaxScaler()
    X_train_scaled = scaler_mlp.fit_transform(X_train)
    X_test_scaled = scaler_mlp.transform(X_test)

    mlp = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=1000,
                       random_state=42, early_stopping=True, validation_fraction=0.2)
    mlp.fit(X_train_scaled, y_train)
    y_pred_mlp = mlp.predict(X_test_scaled)
    y_pred_mlp = np.clip(y_pred_mlp, 0, 1)

    r2_mlp = r2_score(y_test, y_pred_mlp)
    mae_mlp = mean_absolute_error(y_test, y_pred_mlp)
    rmse_mlp = np.sqrt(mean_squared_error(y_test, y_pred_mlp))
    bias_mlp = np.mean(y_pred_mlp - y_test)
    oob_mlp = np.mean((y_pred_mlp < 0) | (y_pred_mlp > 1))

    metrics_lopo.append({
        'validation_type': 'sp2_lopo',
        'fold': test_profile,
        'model': 'MLP',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2_mlp, 4),
        'MAE': round(mae_mlp, 4),
        'RMSE': round(rmse_mlp, 4),
        'bias': round(bias_mlp, 4),
        'oob_rate': round(oob_mlp, 4)
    })

    print(f"  {test_profile}: Ridge R²={r2_ridge:.4f}, MLP R²={r2_mlp:.4f}")

# ============================================================================
# VALIDATION 2: SP2 LEAVE-ONE-TEMPERATURE-OUT (LOTO)
# ============================================================================
print("\n[2] SP2 LEAVE-ONE-TEMPERATURE-OUT CROSS-VALIDATION")
print("=" * 80)

df_sp2['temp'] = df_sp2['temperature_condition'].str.strip() if 'temperature_condition' in df_sp2.columns else 'unknown'
temperatures = sorted(df_sp2['temp'].unique())

print(f"Temperatures: {temperatures}")

metrics_loto = []
for test_temp in temperatures:
    train_idx = df_sp2['temp'] != test_temp
    test_idx = df_sp2['temp'] == test_temp

    X_train = df_sp2.loc[train_idx, feature_cols].copy()
    y_train = df_sp2.loc[train_idx, target_col].copy()
    X_test = df_sp2.loc[test_idx, feature_cols].copy()
    y_test = df_sp2.loc[test_idx, target_col].copy()

    if len(X_train) < 100 or len(X_test) < 100:
        print(f"  {test_temp}: SKIP (insufficient data)")
        continue

    # Ridge
    scaler_ridge = MinMaxScaler()
    X_train_scaled = scaler_ridge.fit_transform(X_train)
    X_test_scaled = scaler_ridge.transform(X_test)

    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_scaled, y_train)
    y_pred_ridge = ridge.predict(X_test_scaled)

    r2_ridge = r2_score(y_test, y_pred_ridge)
    mae_ridge = mean_absolute_error(y_test, y_pred_ridge)
    rmse_ridge = np.sqrt(mean_squared_error(y_test, y_pred_ridge))
    bias_ridge = np.mean(y_pred_ridge - y_test)
    oob_ridge = np.mean((y_pred_ridge < 0) | (y_pred_ridge > 1))

    metrics_loto.append({
        'validation_type': 'sp2_loto',
        'fold': test_temp,
        'model': 'Ridge',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2_ridge, 4),
        'MAE': round(mae_ridge, 4),
        'RMSE': round(rmse_ridge, 4),
        'bias': round(bias_ridge, 4),
        'oob_rate': round(oob_ridge, 4)
    })

    # MLP
    scaler_mlp = MinMaxScaler()
    X_train_scaled = scaler_mlp.fit_transform(X_train)
    X_test_scaled = scaler_mlp.transform(X_test)

    mlp = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=1000,
                       random_state=42, early_stopping=True, validation_fraction=0.2)
    mlp.fit(X_train_scaled, y_train)
    y_pred_mlp = mlp.predict(X_test_scaled)
    y_pred_mlp = np.clip(y_pred_mlp, 0, 1)

    r2_mlp = r2_score(y_test, y_pred_mlp)
    mae_mlp = mean_absolute_error(y_test, y_pred_mlp)
    rmse_mlp = np.sqrt(mean_squared_error(y_test, y_pred_mlp))
    bias_mlp = np.mean(y_pred_mlp - y_test)
    oob_mlp = np.mean((y_pred_mlp < 0) | (y_pred_mlp > 1))

    metrics_loto.append({
        'validation_type': 'sp2_loto',
        'fold': test_temp,
        'model': 'MLP',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2_mlp, 4),
        'MAE': round(mae_mlp, 4),
        'RMSE': round(rmse_mlp, 4),
        'bias': round(bias_mlp, 4),
        'oob_rate': round(oob_mlp, 4)
    })

    print(f"  {test_temp}: Ridge R²={r2_ridge:.4f}, MLP R²={r2_mlp:.4f}")

# Save SP2 metrics
sp2_metrics = pd.DataFrame(metrics_lopo + metrics_loto)
sp2_lopo_path = ODIR / "sp2_leave_one_profile_out_metrics.csv"
sp2_loto_path = ODIR / "sp2_leave_one_temperature_out_metrics.csv"

pd.DataFrame(metrics_lopo).to_csv(sp2_lopo_path, index=False)
pd.DataFrame(metrics_loto).to_csv(sp2_loto_path, index=False)

print(f"\n[OK] SP2 LOPO: {sp2_lopo_path}")
print(f"[OK] SP2 LOTO: {sp2_loto_path}")

# ============================================================================
# VALIDATION 3: MULTI-DOMAIN BENCHMARK
# ============================================================================
print("\n[3] MULTI-DOMAIN BENCHMARK (Oxford + LG + IoT + SP2)")
print("=" * 80)

domains_data = {}

# Load SP2
print("Loading SP2...")
domains_data['SP2'] = {
    'df': df_sp2[feature_cols + [target_col]].sample(min(60000, len(df_sp2)), random_state=42).reset_index(drop=True),
    'name': 'SP2 Dynamic Profiles'
}
print(f"  SP2: {len(domains_data['SP2']['df'])} rows")

# Load IoT
print("Loading IoT...")
try:
    df_iot = pd.read_parquet(ROOT / "outputs/external_datasets/iot_method_b_extracted.parquet")
    df_iot = df_iot.dropna(subset=feature_cols + ['soc_method_b_soc_windowed'])
    df_iot = df_iot.rename(columns={'soc_method_b_soc_windowed': target_col})
    domains_data['IoT'] = {
        'df': df_iot[feature_cols + [target_col]].reset_index(drop=True),
        'name': 'IoT Field'
    }
    print(f"  IoT: {len(domains_data['IoT']['df'])} rows")
except:
    print("  IoT: NOT FOUND")

# Load LG (stable-core preferred)
print("Loading LG...")
try:
    df_lg = pd.read_parquet(ROOT / "data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet")

    # Exclude known OOD cells
    ood_cells = {549, 562, 575, 582, 607, 551, 555, 593}
    if 'cell_id' in df_lg.columns:
        df_lg = df_lg[~df_lg['cell_id'].isin(ood_cells)]

    df_lg = df_lg.dropna(subset=feature_cols + ['method_b_lg_recomputed'])
    df_lg = df_lg.rename(columns={'method_b_lg_recomputed': target_col})
    df_lg = df_lg[feature_cols + [target_col]].sample(min(60000, len(df_lg)), random_state=42).reset_index(drop=True)

    domains_data['LG'] = {
        'df': df_lg,
        'name': 'LG18650 HG2'
    }
    print(f"  LG: {len(domains_data['LG']['df'])} rows")
except Exception as e:
    print(f"  LG: NOT FOUND ({e})")

# Oxford: attempt to load from CORE (optional)
print("Loading Oxford...")
oxford_candidates = [
    ROOT / "CORE/outputs/stage4c_final_results.parquet",
    ROOT / "CORE/stage4c_final_results/stage4c_final_results.parquet",
]
oxford_found = False
for candidate in oxford_candidates:
    if candidate.exists():
        try:
            df_oxford = pd.read_parquet(candidate)
            if 'method_b_soc_q_cycle' in df_oxford.columns:
                df_oxford = df_oxford.rename(columns={'method_b_soc_q_cycle': target_col})
            df_oxford = df_oxford.dropna(subset=feature_cols + [target_col])
            df_oxford = df_oxford[feature_cols + [target_col]].sample(min(60000, len(df_oxford)), random_state=42).reset_index(drop=True)
            domains_data['Oxford'] = {
                'df': df_oxford,
                'name': 'Oxford Stage4C Lab Baseline'
            }
            print(f"  Oxford: {len(domains_data['Oxford']['df'])} rows")
            oxford_found = True
            break
        except:
            pass

if not oxford_found:
    print("  Oxford: NOT FOUND (using 3-domain benchmark)")

print(f"\nBenchmark domains: {list(domains_data.keys())}")

# Multi-domain cross-validation matrix
metrics_multidomain = []
status_multidomain = []

for train_domain in domains_data.keys():
    for test_domain in domains_data.keys():
        if train_domain == test_domain:
            status_multidomain.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': 'Ridge',
                'status': 'SKIP_SAME_DOMAIN'
            })
            status_multidomain.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': 'MLP',
                'status': 'SKIP_SAME_DOMAIN'
            })
            continue

        try:
            X_train = domains_data[train_domain]['df'][feature_cols].copy()
            y_train = domains_data[train_domain]['df'][target_col].copy()
            X_test = domains_data[test_domain]['df'][feature_cols].copy()
            y_test = domains_data[test_domain]['df'][target_col].copy()

            # Ridge
            scaler = MinMaxScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            ridge = Ridge(alpha=1.0)
            ridge.fit(X_train_scaled, y_train)
            y_pred = ridge.predict(X_test_scaled)

            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))

            metrics_multidomain.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': 'Ridge',
                'train_rows': len(X_train),
                'test_rows': len(X_test),
                'R2': round(r2, 4),
                'MAE': round(mae, 4),
                'RMSE': round(rmse, 4),
                'status': 'OK'
            })

            status_multidomain.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': 'Ridge',
                'status': 'OK'
            })

            # MLP
            scaler = MinMaxScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            mlp = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=1000,
                              random_state=42, early_stopping=True, validation_fraction=0.2)
            mlp.fit(X_train_scaled, y_train)
            y_pred = mlp.predict(X_test_scaled)
            y_pred = np.clip(y_pred, 0, 1)

            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))

            metrics_multidomain.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': 'MLP',
                'train_rows': len(X_train),
                'test_rows': len(X_test),
                'R2': round(r2, 4),
                'MAE': round(mae, 4),
                'RMSE': round(rmse, 4),
                'status': 'OK'
            })

            status_multidomain.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': 'MLP',
                'status': 'OK'
            })

            print(f"  {train_domain} → {test_domain}: Ridge R²={r2:.4f}")

        except Exception as e:
            print(f"  {train_domain} → {test_domain}: ERROR ({str(e)[:50]})")
            status_multidomain.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': 'Ridge',
                'status': f'ERROR: {str(e)[:40]}'
            })
            status_multidomain.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': 'MLP',
                'status': f'ERROR: {str(e)[:40]}'
            })

# Save multi-domain metrics
multidomain_metrics_path = ODIR / "method_b_multidomain_benchmark_metrics.csv"
multidomain_status_path = ODIR / "method_b_multidomain_benchmark_status.csv"

pd.DataFrame(metrics_multidomain).to_csv(multidomain_metrics_path, index=False)
pd.DataFrame(status_multidomain).to_csv(multidomain_status_path, index=False)

print(f"\n[OK] Multi-domain metrics: {multidomain_metrics_path}")
print(f"[OK] Multi-domain status: {multidomain_status_path}")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)

# SP2 LOPO
print("\nSP2 Leave-One-Profile-Out:")
lopo_ridge = pd.DataFrame(metrics_lopo)[pd.DataFrame(metrics_lopo)['model'] == 'Ridge']
lopo_mlp = pd.DataFrame(metrics_lopo)[pd.DataFrame(metrics_lopo)['model'] == 'MLP']

print(f"  Ridge: R² = {lopo_ridge['R2'].mean():.4f} ± {lopo_ridge['R2'].std():.4f}")
print(f"  MLP:   R² = {lopo_mlp['R2'].mean():.4f} ± {lopo_mlp['R2'].std():.4f}")
print(f"  Best Ridge: {lopo_ridge.loc[lopo_ridge['R2'].idxmax(), 'fold']} ({lopo_ridge['R2'].max():.4f})")
print(f"  Worst Ridge: {lopo_ridge.loc[lopo_ridge['R2'].idxmin(), 'fold']} ({lopo_ridge['R2'].min():.4f})")

# SP2 LOTO
print("\nSP2 Leave-One-Temperature-Out:")
loto_ridge = pd.DataFrame(metrics_loto)[pd.DataFrame(metrics_loto)['model'] == 'Ridge']
loto_mlp = pd.DataFrame(metrics_loto)[pd.DataFrame(metrics_loto)['model'] == 'MLP']

if len(loto_ridge) > 0:
    print(f"  Ridge: R² = {loto_ridge['R2'].mean():.4f} ± {loto_ridge['R2'].std():.4f}")
    print(f"  MLP:   R² = {loto_mlp['R2'].mean():.4f} ± {loto_mlp['R2'].std():.4f}")
else:
    print("  No temperature folds available")

# Multi-domain
print("\nMulti-Domain Benchmark:")
md_ridge = pd.DataFrame(metrics_multidomain)[pd.DataFrame(metrics_multidomain)['model'] == 'Ridge']
if len(md_ridge) > 0:
    print(f"  Ridge best R²: {md_ridge['R2'].max():.4f} ({md_ridge.loc[md_ridge['R2'].idxmax(), 'train_domain']} → {md_ridge.loc[md_ridge['R2'].idxmax(), 'test_domain']})")
    print(f"  Ridge worst R²: {md_ridge['R2'].min():.4f} ({md_ridge.loc[md_ridge['R2'].idxmin(), 'train_domain']} → {md_ridge.loc[md_ridge['R2'].idxmin(), 'test_domain']})")

print("\n" + "=" * 80)
print("[OK] All validations complete")
print("=" * 80)
