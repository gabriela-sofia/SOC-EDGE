#!/usr/bin/env python3
"""IoT Method B Model Improvement v2 (Ridge + MLP only, fast)"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[1]
ODIR = ROOT / "outputs/external_datasets"
MDIR = ROOT / "models_external"
MDIR.mkdir(parents=True, exist_ok=True)

print("IoT Method B Model Improvement v2 (Fast)")
print("=" * 80)

# Load
print("\nLoading IoT data...")
df = pd.read_parquet(ODIR / "iot_method_b_extracted.parquet")

# Normalize columns
feature_cols = ['voltage_V', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
if 'voltage_v' in df.columns:
    df['voltage_V'] = df['voltage_v']
if 'current_ma' in df.columns:
    df['current_abs_A'] = df['current_ma'] / 1000.0
if 'temperature_c' in df.columns:
    df['temperature_C'] = df['temperature_c']

# Compute deltas
if 'delta_voltage' not in df.columns:
    df['delta_voltage'] = df.groupby('node_id')['voltage_V'].diff().fillna(0)
if 'delta_temperature' not in df.columns:
    df['delta_temperature'] = df.groupby('node_id')['temperature_C'].diff().fillna(0)
if 'delta_current' not in df.columns:
    df['delta_current'] = df.groupby('node_id')['current_abs_A'].diff().fillna(0)

target_col = 'soc_method_b'
if 'soc_method_b_soc_windowed' in df.columns:
    df[target_col] = df['soc_method_b_soc_windowed']

# Filter
df = df.dropna(subset=feature_cols + [target_col])
df = df[(df[target_col] >= 0) & (df[target_col] <= 1)]

print(f"Total rows: {len(df)}")
print(f"Nodes: {df['node_id'].nunique()}")

# Valid nodes
node_counts = df['node_id'].value_counts()
valid_nodes = node_counts[node_counts >= 30].index.tolist()
df = df[df['node_id'].isin(valid_nodes)].reset_index(drop=True)

print(f"Nodes with >=30 samples: {len(valid_nodes)}")
print(f"Final rows: {len(df)}")

# LONO
print("\nLeave-One-Node-Out Validation")
print("=" * 80)

metrics_list = []

for test_node in sorted(valid_nodes):
    train_idx = df['node_id'] != test_node
    test_idx = df['node_id'] == test_node

    X_train = df.loc[train_idx, feature_cols].copy()
    y_train = df.loc[train_idx, target_col].copy()
    X_test = df.loc[test_idx, feature_cols].copy()
    y_test = df.loc[test_idx, target_col].copy()

    if len(X_test) < 10:
        continue

    scaler = MinMaxScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Ridge
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_s, y_train)
    y_pred_ridge = np.clip(ridge.predict(X_test_s), 0, 1)

    r2_ridge = r2_score(y_test, y_pred_ridge)
    mae_ridge = mean_absolute_error(y_test, y_pred_ridge)
    rmse_ridge = np.sqrt(mean_squared_error(y_test, y_pred_ridge))
    bias_ridge = np.mean(y_pred_ridge - y_test)
    oob_ridge = np.mean((y_pred_ridge < 0) | (y_pred_ridge > 1))

    metrics_list.append({
        'node': test_node,
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
        'target_max': round(y_test.max(), 4),
        'oob_rate': round(oob_ridge, 4)
    })

    # MLP
    mlp = MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=500, random_state=42, early_stopping=True, validation_fraction=0.2)
    mlp.fit(X_train_s, y_train)
    y_pred_mlp = np.clip(mlp.predict(X_test_s), 0, 1)

    r2_mlp = r2_score(y_test, y_pred_mlp)
    mae_mlp = mean_absolute_error(y_test, y_pred_mlp)
    rmse_mlp = np.sqrt(mean_squared_error(y_test, y_pred_mlp))
    bias_mlp = np.mean(y_pred_mlp - y_test)
    oob_mlp = np.mean((y_pred_mlp < 0) | (y_pred_mlp > 1))

    metrics_list.append({
        'node': test_node,
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
        'target_max': round(y_test.max(), 4),
        'oob_rate': round(oob_mlp, 4)
    })

    print(f"  Node {test_node}: Ridge R²={r2_ridge:.4f}, MLP R²={r2_mlp:.4f}")

# Save
metrics_df = pd.DataFrame(metrics_list)
metrics_df.to_csv(ODIR / "iot_method_b_model_comparison_v2.csv", index=False)

# Error analysis
error_analysis = []
for model_name in ['Ridge', 'MLP']:
    model_metrics = metrics_df[metrics_df['model'] == model_name]
    if len(model_metrics) == 0:
        continue

    mean_r2 = model_metrics['R2'].mean()
    mean_mae = model_metrics['MAE'].mean()
    mean_rmse = model_metrics['RMSE'].mean()

    print(f"\n{model_name}: Mean R²={mean_r2:.4f}, MAE={mean_mae:.4f}, RMSE={mean_rmse:.4f}")

error_df = pd.DataFrame(error_analysis)
error_df.to_csv(ODIR / "iot_method_b_error_analysis_v2.csv", index=False)

# Feature ranges
feature_contract = []
for col in feature_cols:
    feature_contract.append({
        'feature': col,
        'min': round(df[col].min(), 6),
        'max': round(df[col].max(), 6),
        'mean': round(df[col].mean(), 6),
        'std': round(df[col].std(), 6),
        'unit': 'V' if 'voltage' in col else 'C' if 'temperature' in col else 'A'
    })

feature_df = pd.DataFrame(feature_contract)
feature_df.to_csv(ODIR / "iot_method_b_feature_range_contract_v2.csv", index=False)

# Selection
best_model = metrics_df.groupby('model')['R2'].mean().idxmax()
best_r2 = metrics_df.groupby('model')['R2'].mean().max()

print(f"\nBest Model: {best_model} (R²={best_r2:.4f})")

candidate = best_model
reason = f"{best_model} has best R² and is convertible to TF Lite"

candidate_df = pd.DataFrame([{
    'model': candidate,
    'reason': reason,
    'best_scientific': best_model,
    'convertible': candidate in ['MLP', 'Ridge']
}])
candidate_df.to_csv(ODIR / "iot_method_b_candidate_selection_v2.csv", index=False)

print(f"ESP32 Candidate: {candidate}\n")
print("[OK] Complete\n")
