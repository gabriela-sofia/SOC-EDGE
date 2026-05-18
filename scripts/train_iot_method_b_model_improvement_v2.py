#!/usr/bin/env python3
"""
IoT Method B Model Improvement v2
Leave-One-Node-Out validation with Ridge, RandomForest, GradientBoosting, MLP
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor
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

print("IoT Method B Model Improvement v2")
print("=" * 80)

# Load data
print("\nLoading IoT data...")
df = pd.read_parquet(ODIR / "iot_method_b_extracted.parquet")

# Normalize column names
feature_cols = ['voltage_V', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
if 'voltage_v' in df.columns:
    df['voltage_V'] = df['voltage_v']
if 'current_ma' in df.columns:
    df['current_abs_A'] = df['current_ma'] / 1000.0
elif 'current_abs_a' in df.columns:
    df['current_abs_A'] = df['current_abs_a']
if 'temperature_c' in df.columns:
    df['temperature_C'] = df['temperature_c']

# Compute deltas if missing
if 'delta_voltage' not in df.columns:
    df['delta_voltage'] = df.groupby('node_id')['voltage_V'].diff().fillna(0)
if 'delta_temperature' not in df.columns:
    df['delta_temperature'] = df.groupby('node_id')['temperature_C'].diff().fillna(0)
if 'delta_current' not in df.columns:
    df['delta_current'] = df.groupby('node_id')['current_abs_A'].diff().fillna(0)

target_col = 'soc_method_b'
if 'soc_method_b_soc_windowed' in df.columns:
    df[target_col] = df['soc_method_b_soc_windowed']

# Filter valid
df = df.dropna(subset=feature_cols + [target_col])
df = df[(df[target_col] >= 0) & (df[target_col] <= 1)]

print(f"Total rows: {len(df)}")
print(f"Nodes: {df['node_id'].nunique()}")
print(f"Feature ranges:")
for col in feature_cols:
    print(f"  {col}: {df[col].min():.4f} to {df[col].max():.4f}")

# Get nodes with sufficient data
node_counts = df['node_id'].value_counts()
valid_nodes = node_counts[node_counts >= 30].index.tolist()
print(f"Nodes with >=30 samples: {len(valid_nodes)}")

df = df[df['node_id'].isin(valid_nodes)].reset_index(drop=True)

# ============================================================================
# LEAVE-ONE-NODE-OUT CROSS-VALIDATION
# ============================================================================
print("\nLeave-One-Node-Out Cross-Validation")
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

    # Scale
    scaler = MinMaxScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Ridge
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train_s, y_train)
    y_pred_ridge = ridge.predict(X_test_s)
    y_pred_ridge = np.clip(y_pred_ridge, 0, 1)

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

    # RandomForest (small)
    try:
        rf = RandomForestRegressor(n_estimators=20, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X_train_s, y_train)
        y_pred_rf = rf.predict(X_test_s)
        y_pred_rf = np.clip(y_pred_rf, 0, 1)

        r2_rf = r2_score(y_test, y_pred_rf)
        mae_rf = mean_absolute_error(y_test, y_pred_rf)
        rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))
        bias_rf = np.mean(y_pred_rf - y_test)
        oob_rf = np.mean((y_pred_rf < 0) | (y_pred_rf > 1))

        metrics_list.append({
            'node': test_node,
            'model': 'RF',
            'train_rows': len(X_train),
            'test_rows': len(X_test),
            'R2': round(r2_rf, 4),
            'MAE': round(mae_rf, 4),
            'RMSE': round(rmse_rf, 4),
            'bias': round(bias_rf, 4),
            'pred_min': round(y_pred_rf.min(), 4),
            'pred_max': round(y_pred_rf.max(), 4),
            'target_min': round(y_test.min(), 4),
            'target_max': round(y_test.max(), 4),
            'oob_rate': round(oob_rf, 4)
        })
    except:
        pass

    # GradientBoosting (small)
    try:
        gb = HistGradientBoostingRegressor(max_iter=50, max_depth=5, learning_rate=0.1, random_state=42)
        gb.fit(X_train_s, y_train)
        y_pred_gb = gb.predict(X_test_s)
        y_pred_gb = np.clip(y_pred_gb, 0, 1)

        r2_gb = r2_score(y_test, y_pred_gb)
        mae_gb = mean_absolute_error(y_test, y_pred_gb)
        rmse_gb = np.sqrt(mean_squared_error(y_test, y_pred_gb))
        bias_gb = np.mean(y_pred_gb - y_test)
        oob_gb = np.mean((y_pred_gb < 0) | (y_pred_gb > 1))

        metrics_list.append({
            'node': test_node,
            'model': 'GB',
            'train_rows': len(X_train),
            'test_rows': len(X_test),
            'R2': round(r2_gb, 4),
            'MAE': round(mae_gb, 4),
            'RMSE': round(rmse_gb, 4),
            'bias': round(bias_gb, 4),
            'pred_min': round(y_pred_gb.min(), 4),
            'pred_max': round(y_pred_gb.max(), 4),
            'target_min': round(y_test.min(), 4),
            'target_max': round(y_test.max(), 4),
            'oob_rate': round(oob_gb, 4)
        })
    except:
        pass

    # MLP (lightweight)
    try:
        mlp = MLPRegressor(hidden_layer_sizes=(32, 16), max_iter=500, random_state=42, early_stopping=True, validation_fraction=0.2)
        mlp.fit(X_train_s, y_train)
        y_pred_mlp = mlp.predict(X_test_s)
        y_pred_mlp = np.clip(y_pred_mlp, 0, 1)

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
    except:
        pass

    print(f"  Node {test_node}: Ridge R2={r2_ridge:.4f}, GB R2={r2_gb if 'r2_gb' in locals() else 'N/A'}, MLP R2={r2_mlp if 'r2_mlp' in locals() else 'N/A'}")

# Save metrics
metrics_df = pd.DataFrame(metrics_list)
metrics_df.to_csv(ODIR / "iot_method_b_model_comparison_v2.csv", index=False)

print(f"\n[OK] Metrics saved")

# ============================================================================
# ERROR ANALYSIS BY SOC RANGE
# ============================================================================
print("\nError Analysis by SOC Range")
print("=" * 80)

error_analysis = []

for model_name in ['Ridge', 'RF', 'GB', 'MLP']:
    model_metrics = metrics_df[metrics_df['model'] == model_name]
    if len(model_metrics) == 0:
        continue

    mean_r2 = model_metrics['R2'].mean()
    mean_mae = model_metrics['MAE'].mean()
    mean_rmse = model_metrics['RMSE'].mean()

    print(f"\n{model_name}:")
    print(f"  Mean R²: {mean_r2:.4f}")
    print(f"  Mean MAE: {mean_mae:.4f}")
    print(f"  Mean RMSE: {mean_rmse:.4f}")
    print(f"  Folds: {len(model_metrics)}")

    for _, row in model_metrics.iterrows():
        error_analysis.append({
            'model': model_name,
            'node': row['node'],
            'R2': row['R2'],
            'MAE': row['MAE'],
            'RMSE': row['RMSE'],
            'bias': row['bias'],
            'oob_rate': row['oob_rate']
        })

error_df = pd.DataFrame(error_analysis)
error_df.to_csv(ODIR / "iot_method_b_error_analysis_v2.csv", index=False)

# ============================================================================
# FEATURE RANGE CONTRACT
# ============================================================================
print("\nFeature Range Contract")
print("=" * 80)

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

print(feature_df.to_string(index=False))

# ============================================================================
# MODEL SELECTION FOR ESP32
# ============================================================================
print("\n" + "=" * 80)
print("MODEL SELECTION FOR ESP32")
print("=" * 80)

# Rank models by R2 and size
model_summary = metrics_df.groupby('model').agg({
    'R2': ['mean', 'std'],
    'MAE': 'mean',
    'RMSE': 'mean'
}).round(4)

print("\nModel Performance Summary:")
print(model_summary)

# Choose best
best_model = metrics_df.groupby('model')['R2'].mean().idxmax()
best_r2 = metrics_df.groupby('model')['R2'].mean().max()

print(f"\nBest Model: {best_model} (R²={best_r2:.4f})")

# Candidate for ESP32: prioritize small, stable, convertible
# MLP is convertible to TF Lite; RF/GB hard to convert
candidate_selection = []

if best_model == 'MLP':
    candidate = 'MLP'
    reason = 'Highest R2, convertible to TF Lite'
elif best_model in ['RF', 'GB']:
    candidate = 'MLP'
    reason = f'{best_model} has better R2 but hard to convert to TF Lite. MLP is best convertible option.'
else:
    candidate = 'Ridge'
    reason = 'Simple, small, fast; adequate for field deployment'

candidate_selection.append({
    'model': candidate,
    'reason': reason,
    'best_scientific_model': best_model,
    'esp32_convertible': candidate in ['MLP', 'Ridge']
})

candidate_df = pd.DataFrame(candidate_selection)
candidate_df.to_csv(ODIR / "iot_method_b_candidate_selection_v2.csv", index=False)

print(f"\nCandidates for ESP32: {candidate}")
print(f"Reason: {reason}")

print("\n[OK] Complete\n")
