#!/usr/bin/env python3
"""Fast LG-only training - streaming approach"""
import pandas as pd
import numpy as np
import glob
import pickle
import os
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

print("TRAIN LG-ONLY - FAST MODE\n")

# Load all valid parts (skip corrupt early parts 0-30)
all_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_*.parquet"))
parts_valid = all_parts[40:]  # Skip corrupt parts 0-30

print("Loading " + str(len(parts_valid)) + " valid parts...")
dfs = []
for i, p in enumerate(parts_valid):
    try:
        dfs.append(pd.read_parquet(p))
        if (i+1) % 5 == 0:
            print("  " + str(i+1) + " parts loaded")
    except:
        pass

df = pd.concat(dfs, ignore_index=True)
print("Loaded " + str(len(df)) + " rows\n")

cells = sorted(df['cell_id'].unique())
print("Found cells: " + str(cells) + "\n")

features_6 = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
metrics = []

for test_cell in cells:
    train_df = df[df['cell_id'] != test_cell]
    test_df = df[df['cell_id'] == test_cell]

    X_train = train_df[features_6].values
    y_train = train_df['soc_target'].values
    X_test = test_df[features_6].values
    y_test = test_df['soc_target'].values

    scaler = MinMaxScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = MLPRegressor(hidden_layer_sizes=(64,32), max_iter=500, random_state=42)
    model.fit(X_train_s, y_train)
    y_pred = model.predict(X_test_s)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print("Cell " + str(test_cell) + ": R2=" + str(round(r2, 4)) + " MAE=" + str(round(mae, 4)))

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

metrics_df = pd.DataFrame(metrics)
metrics_df.to_csv("outputs/external_datasets/lg_only_method_b_cross_cell_metrics.csv", index=False)
print("\nMetrics saved")
print("\nSummary:")
print("R2 mean: " + str(round(metrics_df['R2'].mean(), 4)))
print("MAE mean: " + str(round(metrics_df['MAE'].mean(), 4)))
print("RMSE mean: " + str(round(metrics_df['RMSE'].mean(), 4)))
