#!/usr/bin/env python3
"""
SP2 Method B Diagnostic Training
=================================
Leave-one-profile-out + leave-one-temperature-out cross-validation
Ridge baseline + lightweight MLP
Purpose: Assess SP2 Method B learnability (diagnostic only, not production)
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import pickle
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT = Path("/sessions/eager-stoic-euler/mnt/SOC")
ODIR = ROOT / "outputs/external_datasets"
MDIR = ROOT / "models_external"
MDIR.mkdir(parents=True, exist_ok=True)

print("SP2 Method B Diagnostic Training\n" + "="*70)

# Load data
df = pd.read_parquet(ROOT / "data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet")

# Features and target
feature_cols = ['voltage_V', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
                'delta_voltage', 'delta_temperature', 'delta_current']
target_col = 'soc_method_b_sp'

# Remove NaN in target and features
df = df.dropna(subset=feature_cols + [target_col])

# Extract metadata
df['profile'] = df['profile_type'].str.strip()
df['temp'] = df['temperature_condition'].str.strip()

profiles = df['profile'].unique()
temperatures = df['temp'].unique()

print("Data shape: " + str(df.shape))
print("Profiles: " + str(sorted(profiles)))
print("Temperatures: " + str(sorted(temperatures)))

# Protocol 1: Leave-one-profile-out
print("\n" + "="*70)
print("Protocol 1: Leave-One-Profile-Out")
print("="*70)

metrics_lopo = []

for test_profile in profiles:
    train_idx = df['profile'] != test_profile
    test_idx = df['profile'] == test_profile

    X_train = df.loc[train_idx, feature_cols].copy()
    y_train = df.loc[train_idx, target_col].copy()
    X_test = df.loc[test_idx, feature_cols].copy()
    y_test = df.loc[test_idx, target_col].copy()

    if len(X_train) < 100 or len(X_test) < 100:
        print("  " + test_profile + ": Skip (insufficient data)")
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

    metrics_lopo.append({
        'validation_type': 'leave_one_profile_out',
        'fold': test_profile,
        'model': 'Ridge',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2_ridge, 4),
        'MAE': round(mae_ridge, 4),
        'RMSE': round(rmse_ridge, 4),
        'bias': round(bias_ridge, 4),
        'pred_min': round(y_pred_ridge.min(), 4),
        'pred_max': round(y_pred_ridge.max(), 4),
        'target_min': round(y_test.min(), 4),
        'target_max': round(y_test.max(), 4)
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

    metrics_lopo.append({
        'validation_type': 'leave_one_profile_out',
        'fold': test_profile,
        'model': 'MLP',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2_mlp, 4),
        'MAE': round(mae_mlp, 4),
        'RMSE': round(rmse_mlp, 4),
        'bias': round(bias_mlp, 4),
        'pred_min': round(y_pred_mlp.min(), 4),
        'pred_max': round(y_pred_mlp.max(), 4),
        'target_min': round(y_test.min(), 4),
        'target_max': round(y_test.max(), 4)
    })

    r2r = "{:.4f}".format(r2_ridge)
    r2m = "{:.4f}".format(r2_mlp)
    print("  " + test_profile + ": Ridge R2=" + r2r + ", MLP R2=" + r2m)

# Protocol 2: Leave-one-temperature-out
print("\n" + "="*70)
print("Protocol 2: Leave-One-Temperature-Out")
print("="*70)

metrics_loto = []

for test_temp in temperatures:
    train_idx = df['temp'] != test_temp
    test_idx = df['temp'] == test_temp

    X_train = df.loc[train_idx, feature_cols].copy()
    y_train = df.loc[train_idx, target_col].copy()
    X_test = df.loc[test_idx, feature_cols].copy()
    y_test = df.loc[test_idx, target_col].copy()

    if len(X_train) < 100 or len(X_test) < 100:
        print("  " + test_temp + ": Skip (insufficient data)")
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

    metrics_loto.append({
        'validation_type': 'leave_one_temperature_out',
        'fold': test_temp,
        'model': 'Ridge',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2_ridge, 4),
        'MAE': round(mae_ridge, 4),
        'RMSE': round(rmse_ridge, 4),
        'bias': round(bias_ridge, 4),
        'pred_min': round(y_pred_ridge.min(), 4),
        'pred_max': round(y_pred_ridge.max(), 4),
        'target_min': round(y_test.min(), 4),
        'target_max': round(y_test.max(), 4)
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

    metrics_loto.append({
        'validation_type': 'leave_one_temperature_out',
        'fold': test_temp,
        'model': 'MLP',
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': round(r2_mlp, 4),
        'MAE': round(mae_mlp, 4),
        'RMSE': round(rmse_mlp, 4),
        'bias': round(bias_mlp, 4),
        'pred_min': round(y_pred_mlp.min(), 4),
        'pred_max': round(y_pred_mlp.max(), 4),
        'target_min': round(y_test.min(), 4),
        'target_max': round(y_test.max(), 4)
    })

    r2r = "{:.4f}".format(r2_ridge)
    r2m = "{:.4f}".format(r2_mlp)
    print("  " + test_temp + ": Ridge R2=" + r2r + ", MLP R2=" + r2m)

# Save metrics
all_metrics = pd.DataFrame(metrics_lopo + metrics_loto)
mp = ODIR / "sp2_method_b_diagnostic_metrics.csv"
all_metrics.to_csv(mp, index=False)
print("\n[OK] Metrics: " + str(mp))

# Train final MLP on full data for diagnostic model export
print("\n" + "="*70)
print("Training final MLP on full data (diagnostic only)")

X = df[feature_cols].copy()
y = df[target_col].copy()

scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

mlp_final = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=1000,
                         random_state=42, early_stopping=False)
mlp_final.fit(X_scaled, y)

# Save pipeline
pipeline = {'scaler': scaler, 'model': mlp_final, 'features': feature_cols}
pkl_path = MDIR / "sp2_method_b_mlp_pipeline.pkl"
with open(pkl_path, 'wb') as f:
    pickle.dump(pipeline, f)
print("[OK] Model pipeline: " + str(pkl_path))

# Summary statistics
print("\n" + "="*70)
print("Summary Statistics")

lopo_ridge = all_metrics[(all_metrics['validation_type'] == 'leave_one_profile_out') & (all_metrics['model'] == 'Ridge')]
lopo_mlp = all_metrics[(all_metrics['validation_type'] == 'leave_one_profile_out') & (all_metrics['model'] == 'MLP')]
loto_ridge = all_metrics[(all_metrics['validation_type'] == 'leave_one_temperature_out') & (all_metrics['model'] == 'Ridge')]
loto_mlp = all_metrics[(all_metrics['validation_type'] == 'leave_one_temperature_out') & (all_metrics['model'] == 'MLP')]

print("\nLeave-One-Profile-Out:")
lopo_r_mean = "{:.4f}".format(lopo_ridge['R2'].mean())
lopo_r_std = "{:.4f}".format(lopo_ridge['R2'].std())
print("  Ridge: R2 = " + lopo_r_mean + " +/- " + lopo_r_std)

lopo_m_mean = "{:.4f}".format(lopo_mlp['R2'].mean())
lopo_m_std = "{:.4f}".format(lopo_mlp['R2'].std())
print("  MLP:   R2 = " + lopo_m_mean + " +/- " + lopo_m_std)
