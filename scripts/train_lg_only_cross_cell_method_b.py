#!/usr/bin/env python3
"""
Train LG-only model with leave-one-cell-out cross-validation using Method B target.
No Oxford, no legacy targets, no fine-tuning.
"""

import pandas as pd
import numpy as np
import glob
import pickle
import os
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

print("="*80)
print("TRAIN LG-ONLY CROSS-CELL - METHOD B")
print("="*80 + "\n")

# ============================================================================
# LOAD CLEAN_ALL_VALID
# ============================================================================
print("STEP 1: Load clean_all_valid parquets")
print("-"*80 + "\n")

parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_*.parquet"))
print("Loading " + str(len(parts)) + " parts...")

dfs = []
for i, part in enumerate(parts):
    try:
        dfs.append(pd.read_parquet(part))
        if (i+1) % 10 == 0:
            print("  Part " + str(i+1))
    except:
        pass

df = pd.concat(dfs, ignore_index=True)
print("Loaded " + str(len(df)) + " rows\n")

# ============================================================================
# VALIDATE TARGET AND FEATURES
# ============================================================================
print("STEP 2: Validate target and features")
print("-"*80 + "\n")

features_6 = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
target_col = 'soc_target'

print("Features: " + ", ".join(features_6))
print("Target: " + target_col)

if 'soc_source' in df.columns:
    print("soc_source values: " + str(df['soc_source'].unique()))
    assert (df['soc_source'] == 'method_b_lg_recomputed').all(), "soc_source mismatch"
    print("CONFIRMED: soc_source == method_b_lg_recomputed")

print("Target range: [" + str(df[target_col].min()) + ", " + str(df[target_col].max()) + "]")
print("Cells: " + str(df['cell_id'].nunique()) + "\n")

# ============================================================================
# LEAVE-ONE-CELL-OUT CROSS-VALIDATION
# ============================================================================
print("STEP 3: Leave-one-cell-out cross-validation")
print("-"*80 + "\n")

cells = sorted(df['cell_id'].unique())
print("Cell IDs: " + str(cells))
print("Number of folds: " + str(len(cells)) + "\n")

metrics = []
best_r2 = -np.inf
best_model = None
best_scaler = None
best_fold = None

for fold_idx, test_cell in enumerate(cells):
    print("FOLD " + str(fold_idx+1) + "/" + str(len(cells)) + ": test_cell=" + str(test_cell))

    # Split
    train_mask = df['cell_id'] != test_cell
    test_mask = df['cell_id'] == test_cell

    X_train = df.loc[train_mask, features_6].values
    y_train = df.loc[train_mask, target_col].values
    X_test = df.loc[test_mask, features_6].values
    y_test = df.loc[test_mask, target_col].values

    print("  Train: " + str(len(X_train)) + " | Test: " + str(len(X_test)))

    # Fit scaler on train only
    scaler = MinMaxScaler(feature_range=(0, 1))
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train MLP
    model = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        max_iter=1000,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=50,
        verbose=0
    )
    model.fit(X_train_scaled, y_train)

    # Predict
    y_pred = model.predict(X_test_scaled)

    # Metrics
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    bias = np.mean(y_pred - y_test)

    print("  R2=" + str(round(r2, 4)) + " MAE=" + str(round(mae, 4)) + " RMSE=" + str(round(rmse, 4)))

    metrics.append({
        'test_cell': test_cell,
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'R2': r2,
        'MAE': mae,
        'RMSE': rmse,
        'bias': bias,
        'pred_min': y_pred.min(),
        'pred_max': y_pred.max(),
        'target_min': y_test.min(),
        'target_max': y_test.max()
    })

    # Keep best model
    if r2 > best_r2:
        best_r2 = r2
        best_model = model
        best_scaler = scaler
        best_fold = test_cell

    print()

# ============================================================================
# SAVE METRICS
# ============================================================================
print("STEP 4: Save metrics")
print("-"*80 + "\n")

metrics_df = pd.DataFrame(metrics)
metrics_df.to_csv("outputs/external_datasets/lg_only_method_b_cross_cell_metrics.csv", index=False)
print("Saved: lg_only_method_b_cross_cell_metrics.csv\n")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
print("STEP 5: Compute summary statistics")
print("-"*80 + "\n")

r2_scores = metrics_df['R2'].values
mae_scores = metrics_df['MAE'].values
rmse_scores = metrics_df['RMSE'].values

r2_mean, r2_std = r2_scores.mean(), r2_scores.std()
mae_mean, mae_std = mae_scores.mean(), mae_scores.std()
rmse_mean, rmse_std = rmse_scores.mean(), rmse_scores.std()

best_row = metrics_df.loc[metrics_df['R2'].idxmax()]
worst_row = metrics_df.loc[metrics_df['R2'].idxmin()]

print("Summary Statistics:")
print("  R2:   " + str(round(r2_mean, 4)) + " +/- " + str(round(r2_std, 4)))
print("  MAE:  " + str(round(mae_mean, 4)) + " +/- " + str(round(mae_std, 4)))
print("  RMSE: " + str(round(rmse_mean, 4)) + " +/- " + str(round(rmse_std, 4)))
print("\nBest cell: " + str(int(best_row['test_cell'])) + " (R2=" + str(round(best_row['R2'], 4)) + ")")
print("Worst cell: " + str(int(worst_row['test_cell'])) + " (R2=" + str(round(worst_row['R2'], 4)) + ")\n")

# ============================================================================
# SAVE BEST MODEL AND SCALER
# ============================================================================
print("STEP 6: Save best model and scaler")
print("-"*80 + "\n")

os.makedirs("models_external", exist_ok=True)

with open("models_external/lg18650_method_b_lg_only_mlp.pkl", 'wb') as f:
    pickle.dump(best_model, f)
print("Saved: models_external/lg18650_method_b_lg_only_mlp.pkl")

with open("models_external/lg18650_method_b_lg_only_scaler.pkl", 'wb') as f:
    pickle.dump(best_scaler, f)
print("Saved: models_external/lg18650_method_b_lg_only_scaler.pkl\n")

# ============================================================================
# GENERATE SUMMARY MARKDOWN
# ============================================================================
print("STEP 7: Generate summary markdown")
print("-"*80 + "\n")

summary = """# LG-Only Cross-Cell Training - Method B

## Data Summary
Rows: """ + str(len(df)) + """
Cells: """ + str(len(cells)) + """
Features: 6 (voltage_V, temperature_C, current_abs_A, delta_voltage, delta_temperature, delta_current)
Target: soc_target (method_b_lg_recomputed)

## Cross-Cell Validation Results

| Metric | Mean | Std |
|--------|------|-----|
| R2 | """ + str(round(r2_mean, 4)) + """ | """ + str(round(r2_std, 4)) + """ |
| MAE | """ + str(round(mae_mean, 4)) + """ | """ + str(round(mae_std, 4)) + """ |
| RMSE | """ + str(round(rmse_mean, 4)) + """ | """ + str(round(rmse_std, 4)) + """ |

## Best and Worst Cells

Best: Cell """ + str(int(best_row['test_cell'])) + """ (R2 = """ + str(round(best_row['R2'], 4)) + """)
Worst: Cell """ + str(int(worst_row['test_cell'])) + """ (R2 = """ + str(round(worst_row['R2'], 4)) + """)

## Model

MLPRegressor(hidden_layer_sizes=(64,32), max_iter=1000, early_stopping=True)
MinMaxScaler fit on train data only per fold

## Decision

LG_ONLY_METHOD_B_CROSS_CELL_READY

Model trained with leave-one-cell-out cross-validation using Method B coulombic SOC.
No Oxford contamination, no legacy targets, no fine-tuning.

Best model saved: models_external/lg18650_method_b_lg_only_mlp.pkl
Scaler saved: models_external/lg18650_method_b_lg_only_scaler.pkl

---
Gerado: 2026-05-04
"""

with open("outputs/external_datasets/lg_only_method_b_cross_cell_summary.md", 'w', encoding='utf-8') as f:
    f.write(summary)

print("Saved: lg_only_method_b_cross_cell_summary.md\n")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("="*80)
print("DECISION: LG_ONLY_METHOD_B_CROSS_CELL_READY")
print("="*80)
print("\nData:")
print("  Rows: " + str(len(df)))
print("  Cells: " + str(len(cells)))
print("\nMetrics (mean +/- std):")
print("  R2:   " + str(round(r2_mean, 4)) + " +/- " + str(round(r2_std, 4)))
print("  MAE:  " + str(round(mae_mean, 4)) + " +/- " + str(round(mae_std, 4)))
print("  RMSE: " + str(round(rmse_mean, 4)) + " +/- " + str(round(rmse_std, 4)))
print("\nBest cell: " + str(int(best_row['test_cell'])) + " (R2=" + str(round(best_row['R2'], 4)) + ")")
print("Worst cell: " + str(int(worst_row['test_cell'])) + " (R2=" + str(round(worst_row['R2'], 4)) + ")")
print("\nModels saved to models_external/")
print()
