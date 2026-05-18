#!/usr/bin/env python3
"""IoT Feature Contract Stress Test - Unit/Preprocessing Error Detection"""

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[1]
ODIR = ROOT / "outputs/external_datasets"
MDIR = ROOT / "models_external"

print("=" * 80)
print("IoT Feature Contract Stress Test")
print("=" * 80)

# Load model first to know exact features
print("\nLoading trained MLP model...")
with open(MDIR / "iot_method_b_mlp_pipeline.pkl", 'rb') as f:
    model_obj = pickle.load(f)

scaler = model_obj['scaler']
mlp = model_obj['model']
feature_names = model_obj.get('features')

print("Model features:", feature_names)
print("Scaler n_features:", scaler.n_features_in_)

# Load data
print("\nLoading IoT data...")
df = pd.read_parquet(ODIR / "iot_method_b_extracted.parquet")

# Compute Method B if needed
target_col = 'soc_method_b'
if target_col not in df.columns:
    if 'q_mah' in df.columns and 'Q_cycle_mah' in df.columns:
        df[target_col] = 1.0 - df['q_mah'].abs() / df['Q_cycle_mah'].clip(lower=1)
        df[target_col] = df[target_col].clip(0, 1)

# Ensure temperature_C column exists
if 'temperature_c' in df.columns:
    df['temperature_C'] = df['temperature_c']

# Compute deltas if missing
if 'delta_voltage' not in df.columns:
    df['delta_voltage'] = df.groupby('node_id')['voltage_V'].diff().fillna(0) if 'voltage_V' in df.columns else df.groupby('node_id')['voltage_v'].diff().fillna(0)
if 'delta_temperature' not in df.columns:
    df['delta_temperature'] = df.groupby('node_id')['temperature_C'].diff().fillna(0)
if 'delta_current' not in df.columns:
    df['delta_current'] = df.groupby('node_id')['current_ma'].diff().fillna(0) if 'current_ma' in df.columns else 0

# Filter valid
df = df.dropna(subset=feature_names + [target_col])
df = df[(df[target_col] >= 0) & (df[target_col] <= 1)]

print("Total rows: {}".format(len(df)))
print("Nodes: {}".format(df['node_id'].nunique()))

# Get nodes with sufficient data
node_counts = df['node_id'].value_counts()
valid_nodes = node_counts[node_counts >= 30].index.tolist()
df = df[df['node_id'].isin(valid_nodes)].reset_index(drop=True)

# Sample test data
np.random.seed(42)
test_size = 500
test_df = df.sample(n=min(test_size, len(df)), random_state=42)
X_test = test_df[feature_names].copy()
y_test = test_df[target_col].copy()

print("Test set size: {}".format(len(X_test)))
print("\nFeature ranges in test data:")
for col in feature_names:
    print("  {}: {:.6f} to {:.6f}".format(col, X_test[col].min(), X_test[col].max()))

# Helper functions
def safe_predict(X):
    try:
        X_scaled = scaler.transform(X)
        y_pred = mlp.predict(X_scaled)
        y_pred = np.clip(y_pred, 0, 1)
        return y_pred, None
    except Exception as e:
        return None, str(e)[:100]

def compute_metrics(y_true, y_pred):
    if y_pred is None:
        return {'MAE': np.nan, 'RMSE': np.nan, 'bias': np.nan, 'oob_rate': np.nan, 'error_msg': True}
    mae = np.mean(np.abs(y_pred - y_true))
    rmse = np.sqrt(np.mean((y_pred - y_true) ** 2))
    bias = np.mean(y_pred - y_true)
    oob_rate = np.mean((y_pred < 0) | (y_pred > 1))
    return {
        'MAE': round(mae, 4),
        'RMSE': round(rmse, 4),
        'bias': round(bias, 4),
        'oob_rate': round(oob_rate, 4),
        'error_msg': False
    }

# Test scenarios
print("\n" + "=" * 80)
print("STRESS TEST SCENARIOS")
print("=" * 80)

test_results = []

# Scenario 0: Baseline
print("\n[0] BASELINE: All features correct")
y_pred, err = safe_predict(X_test)
metrics = compute_metrics(y_test.values, y_pred) if err is None else {'error_msg': True}
print("  MAE={}, RMSE={}, OOB_rate={}".format(metrics.get('MAE', 'ERROR'), metrics.get('RMSE', 'ERROR'), metrics.get('oob_rate', 'ERROR')))
test_results.append({'scenario': 0, 'name': 'BASELINE: correct', 'severity': 'REFERENCE', **metrics})

# Scenario 1: Current in mA
print("\n[1] UNIT_ERROR: current_ma x1000 (mA to uA)")
X_test_1 = X_test.copy()
X_test_1['current_ma'] = X_test_1['current_ma'] * 1000
X_test_1['delta_current'] = X_test_1['delta_current'] * 1000
print("  current_ma: {:.2f} to {:.2f} (should be ~50-300 mA)".format(X_test_1['current_ma'].min(), X_test_1['current_ma'].max()))
y_pred, err = safe_predict(X_test_1)
metrics = compute_metrics(y_test.values, y_pred) if err is None else {'error_msg': True}
print("  MAE={}, RMSE={}, OOB_rate={}".format(metrics.get('MAE', 'ERROR'), metrics.get('RMSE', 'ERROR'), metrics.get('oob_rate', 'ERROR')))
test_results.append({'scenario': 1, 'name': 'UNIT_ERROR: current_ma x1000', 'severity': 'CRITICAL', **metrics})

# Scenario 2: delta_current in mA
print("\n[2] UNIT_ERROR: delta_current x1000")
X_test_2 = X_test.copy()
X_test_2['delta_current'] = X_test_2['delta_current'] * 1000
print("  delta_current: {:.2f} to {:.2f} (should be ~-0.1 to 0.2)".format(X_test_2['delta_current'].min(), X_test_2['delta_current'].max()))
y_pred, err = safe_predict(X_test_2)
metrics = compute_metrics(y_test.values, y_pred) if err is None else {'error_msg': True}
print("  MAE={}, RMSE={}, OOB_rate={}".format(metrics.get('MAE', 'ERROR'), metrics.get('RMSE', 'ERROR'), metrics.get('oob_rate', 'ERROR')))
test_results.append({'scenario': 2, 'name': 'UNIT_ERROR: delta_current x1000', 'severity': 'HIGH', **metrics})

# Scenario 3: Temperature scale
print("\n[3] UNIT_ERROR: temperature_c x10 (Celsius scale shift)")
X_test_3 = X_test.copy()
X_test_3['temperature_c'] = X_test_3['temperature_c'] * 10
X_test_3['delta_temperature'] = X_test_3['delta_temperature'] * 10
print("  temperature_c: {:.2f} to {:.2f} (should be ~9-46 C)".format(X_test_3['temperature_c'].min(), X_test_3['temperature_c'].max()))
y_pred, err = safe_predict(X_test_3)
metrics = compute_metrics(y_test.values, y_pred) if err is None else {'error_msg': True}
print("  MAE={}, RMSE={}, OOB_rate={}".format(metrics.get('MAE', 'ERROR'), metrics.get('RMSE', 'ERROR'), metrics.get('oob_rate', 'ERROR')))
test_results.append({'scenario': 3, 'name': 'UNIT_ERROR: temperature_c x10', 'severity': 'CRITICAL', **metrics})

# Scenario 4: Feature order shuffled
print("\n[4] FEATURE_ORDER: Features reordered")
X_test_4 = X_test.copy()
cols_shuffled = feature_names.copy()
np.random.shuffle(cols_shuffled)
X_test_4 = X_test_4[cols_shuffled]
print("  Original: {}".format(feature_names))
print("  Shuffled: {}".format(cols_shuffled))
y_pred, err = safe_predict(X_test_4)
metrics = compute_metrics(y_test.values, y_pred) if err is None else {'error_msg': True}
print("  MAE={}, RMSE={}, OOB_rate={}".format(metrics.get('MAE', 'ERROR'), metrics.get('RMSE', 'ERROR'), metrics.get('oob_rate', 'ERROR')))
test_results.append({'scenario': 4, 'name': 'FEATURE_ORDER: shuffled', 'severity': 'CRITICAL', **metrics})

# Scenario 5: Deltas zerados
print("\n[5] MISSING_DELTA: All deltas set to 0")
X_test_5 = X_test.copy()
X_test_5['delta_voltage'] = 0
X_test_5['delta_temperature'] = 0
X_test_5['delta_current'] = 0
y_pred, err = safe_predict(X_test_5)
metrics = compute_metrics(y_test.values, y_pred) if err is None else {'error_msg': True}
print("  MAE={}, RMSE={}, OOB_rate={}".format(metrics.get('MAE', 'ERROR'), metrics.get('RMSE', 'ERROR'), metrics.get('oob_rate', 'ERROR')))
test_results.append({'scenario': 5, 'name': 'MISSING_DELTA: all zeros', 'severity': 'MEDIUM', **metrics})

# Scenario 6: Voltage below range
print("\n[6] OUT_OF_RANGE: voltage_v = 2.5 V")
X_test_6 = X_test.copy()
X_test_6['voltage_v'] = 2.5
print("  voltage_v: 2.5 (training range: 3.83-4.23 V)")
y_pred, err = safe_predict(X_test_6)
metrics = compute_metrics(y_test.values, y_pred) if err is None else {'error_msg': True}
print("  MAE={}, RMSE={}, OOB_rate={}".format(metrics.get('MAE', 'ERROR'), metrics.get('RMSE', 'ERROR'), metrics.get('oob_rate', 'ERROR')))
test_results.append({'scenario': 6, 'name': 'OUT_OF_RANGE: voltage_v 2.5', 'severity': 'HIGH', **metrics})

# Scenario 7: Current above range
print("\n[7] OUT_OF_RANGE: current_ma = 500 mA")
X_test_7 = X_test.copy()
X_test_7['current_ma'] = 500
print("  current_ma: 500 (training range: ~9-300 mA)")
y_pred, err = safe_predict(X_test_7)
metrics = compute_metrics(y_test.values, y_pred) if err is None else {'error_msg': True}
print("  MAE={}, RMSE={}, OOB_rate={}".format(metrics.get('MAE', 'ERROR'), metrics.get('RMSE', 'ERROR'), metrics.get('oob_rate', 'ERROR')))
test_results.append({'scenario': 7, 'name': 'OUT_OF_RANGE: current_ma 500', 'severity': 'HIGH', **metrics})

# Save results
results_df = pd.DataFrame(test_results)
results_df.to_csv(ODIR / "iot_feature_contract_stress_test.csv", index=False)
print("\n[OK] Results saved to CSV")

# Severity ranking
print("\n" + "=" * 80)
print("SEVERITY RANKING")
print("=" * 80)

baseline_row = results_df[results_df['scenario'] == 0]
if len(baseline_row) > 0 and not baseline_row.iloc[0]['error_msg']:
    baseline_mae = baseline_row.iloc[0]['MAE']
    print("\nBaseline MAE: {:.4f}".format(baseline_mae))

    error_scenarios = results_df[results_df['scenario'] > 0].copy()
    error_scenarios = error_scenarios.sort_values('MAE', ascending=False)
    print("\nRanked by impact (highest MAE first):")
    for _, row in error_scenarios.iterrows():
        if row['error_msg']:
            print("  #{}: {} -> ERROR".format(int(row['scenario']), row['name']))
        else:
            mae_val = row['MAE']
            if baseline_mae > 0:
                pct = (mae_val - baseline_mae) / baseline_mae * 100
                print("  #{}: {} -> MAE={:.4f} (delta={:+.1f}%)".format(int(row['scenario']), row['name'], mae_val, pct))
            else:
                print("  #{}: {} -> MAE={:.4f}".format(int(row['scenario']), row['name'], mae_val))

print("\n[OK] Complete")
