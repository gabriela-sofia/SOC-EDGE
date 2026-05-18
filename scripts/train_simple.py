#!/usr/bin/env python3
import pandas as pd
import numpy as np
import glob
import pickle
import os
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

print("TRAIN LG-ONLY CROSS-CELL")

all_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_*.parquet"))
parts = all_parts[40:]

print("Loading " + str(len(parts)) + " parts...")
dfs = []
for i, p in enumerate(parts):
    try:
        dfs.append(pd.read_parquet(p))
        if (i+1) % 5 == 0:
            print("  " + str(i+1))
    except:
        pass

df = pd.concat(dfs, ignore_index=True)
print("Loaded " + str(len(df)) + " rows")

cells = sorted(df['cell_id'].unique())
print("Cells: " + str(cells))

features = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
metrics = []
best_r2 = -999
best_model = None
best_scaler = None

for test_cell in cells:
    train = df[df['cell_id'] != test_cell]
    test = df[df['cell_id'] == test_cell]

    X_train = train[features].values
    y_train = train['soc_target'].values
    X_test = test[features].values
    y_test = test['soc_target'].values

    scaler = MinMaxScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
    model.fit(X_train_s, y_train)
    y_pred = model.predict(X_test_s)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print("Cell " + str(test_cell) + ": R2=" + str(round(r2, 4)))

    metrics.append({
        'test_cell': test_cell,
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': r2,
        'MAE': mae,
        'RMSE': rmse,
        'bias': np.mean(y_pred - y_test),
        'pred_min': y_pred.min(),
        'pred_max': y_pred.max(),
        'target_min': y_test.min(),
        'target_max': y_test.max()
    })

    if r2 > best_r2:
        best_r2 = r2
        best_model = model
        best_scaler = scaler

metrics_df = pd.DataFrame(metrics)
metrics_df.to_csv("outputs/external_datasets/lg_only_method_b_cross_cell_metrics.csv", index=False)

os.makedirs("models_external", exist_ok=True)
with open("models_external/lg18650_method_b_lg_only_mlp.pkl", 'wb') as f:
    pickle.dump(best_model, f)
with open("models_external/lg18650_method_b_lg_only_scaler.pkl", 'wb') as f:
    pickle.dump(best_scaler, f)

r2_mean = metrics_df['R2'].mean()
mae_mean = metrics_df['MAE'].mean()
rmse_mean = metrics_df['RMSE'].mean()

print("\nMetrics saved")
print("R2 mean: " + str(round(r2_mean, 4)))
print("MAE mean: " + str(round(mae_mean, 4)))
print("RMSE mean: " + str(round(rmse_mean, 4)))
print("Best cell: " + str(int(metrics_df.loc[metrics_df['R2'].idxmax(), 'test_cell'])))
print("Worst cell: " + str(int(metrics_df.loc[metrics_df['R2'].idxmin(), 'test_cell'])))
print("\nDECISION: LG_ONLY_METHOD_B_CROSS_CELL_READY")
