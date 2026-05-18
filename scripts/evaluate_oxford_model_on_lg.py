#!/usr/bin/env python3
"""
Evaluate frozen Oxford Stage 4C model on LG clean_all_valid subset.
No training, no fine-tuning, no LG scaler.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import glob
import pickle
import gc
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

print("=" * 70)
print("EVALUATING OXFORD MODEL ON LG CLEAN_ALL_VALID")
print("=" * 70 + "\n")

# ============================================================================
# LOAD OXFORD MODEL AND SCALER
# ============================================================================
print("Loading Oxford model and scaler...")

with open("CORE/stage4c_final_results/models/best_mlp_exp_A_split1.pkl", 'rb') as f:
    model = pickle.load(f)

with open("CORE/stage4c_final_results/models/scaler_exp_A_split1.pkl", 'rb') as f:
    scaler = pickle.load(f)

print("Model loaded: " + str(type(model).__name__))
print("Scaler loaded: " + str(type(scaler).__name__) + "\n")

# ============================================================================
# FEATURE ORDER
# ============================================================================
# Oxford scaler expects 6 features (without current_rel)
feature_cols = ['voltage_V', 'temperature_C', 'current_abs_A',
                'delta_voltage', 'delta_temperature', 'delta_current']

target_col = 'soc_target'

# ============================================================================
# LOAD AND PREDICT ON LG PARQUETS
# ============================================================================
print("Loading LG clean_all_valid parquets...")

lg_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet/part_*.parquet"))
print("Found " + str(len(lg_parts)) + " parquet parts\n")

all_targets = []
all_preds = []
all_preds_clipped = []
all_groups = {'profile_type': [], 'temperature_condition': [], 'cell_id': []}

total_rows = 0

for i, part in enumerate(lg_parts):
    try:
        df = pd.read_parquet(part)
    except:
        continue

    if len(df) == 0:
        continue

    # Extract features and target
    if not all(col in df.columns for col in feature_cols + [target_col]):
        continue

    X = df[feature_cols].values
    y = df[target_col].values

    # Scale using Oxford scaler
    X_scaled = scaler.transform(X)

    # Predict
    y_pred = model.predict(X_scaled)
    y_pred_clipped = np.clip(y_pred, 0, 1)

    # Store
    all_targets.extend(y)
    all_preds.extend(y_pred)
    all_preds_clipped.extend(y_pred_clipped)
    all_groups['profile_type'].extend(df['profile_type'].values)
    all_groups['temperature_condition'].extend(df['temperature_condition'].values)
    all_groups['cell_id'].extend(df['cell_id'].values)

    total_rows += len(df)

    if (i + 1) % 10 == 0:
        print("  Processed " + str(i + 1) + "/" + str(len(lg_parts)) + " parts, " + str(total_rows) + " rows")

    del df, X, y, X_scaled, y_pred, y_pred_clipped
    gc.collect()

print("\nTotal rows evaluated: " + str(total_rows) + "\n")

# ============================================================================
# OVERALL METRICS
# ============================================================================
print("Computing overall metrics...")

all_targets = np.array(all_targets)
all_preds = np.array(all_preds)
all_preds_clipped = np.array(all_preds_clipped)

r2 = r2_score(all_targets, all_preds)
mae = mean_absolute_error(all_targets, all_preds)
rmse = np.sqrt(mean_squared_error(all_targets, all_preds))
bias = np.mean(all_preds - all_targets)

r2_clipped = r2_score(all_targets, all_preds_clipped)
mae_clipped = mean_absolute_error(all_targets, all_preds_clipped)
rmse_clipped = np.sqrt(mean_squared_error(all_targets, all_preds_clipped))

oob_count = np.sum((all_preds < 0) | (all_preds > 1))
oob_pct = (oob_count / len(all_preds) * 100)

print("Overall (raw):")
print("  R2: " + str(round(r2, 4)))
print("  MAE: " + str(round(mae, 4)))
print("  RMSE: " + str(round(rmse, 4)))
print("  Bias: " + str(round(bias, 4)))
print("  Pred range: [" + str(round(all_preds.min(), 3)) + ", " + str(round(all_preds.max(), 3)) + "]")
print("  Target range: [" + str(round(all_targets.min(), 3)) + ", " + str(round(all_targets.max(), 3)) + "]")
print("  OOB (outside [0,1]): " + str(oob_count) + " (" + str(round(oob_pct, 1)) + "%)\n")

print("Overall (clipped):")
print("  R2: " + str(round(r2_clipped, 4)))
print("  MAE: " + str(round(mae_clipped, 4)))
print("  RMSE: " + str(round(rmse_clipped, 4)) + "\n")

# ============================================================================
# GROUP METRICS
# ============================================================================
print("Computing group metrics...")

df_eval = pd.DataFrame({
    'target': all_targets,
    'pred': all_preds,
    'profile_type': all_groups['profile_type'],
    'temperature_condition': all_groups['temperature_condition'],
    'cell_id': all_groups['cell_id']
})

group_metrics = []

for group_col in ['profile_type', 'temperature_condition', 'cell_id']:
    for group_val in df_eval[group_col].unique():
        subset = df_eval[df_eval[group_col] == group_val]

        if len(subset) < 100:
            continue

        r2_g = r2_score(subset['target'], subset['pred'])
        mae_g = mean_absolute_error(subset['target'], subset['pred'])
        rmse_g = np.sqrt(mean_squared_error(subset['target'], subset['pred']))
        bias_g = np.mean(subset['pred'] - subset['target'])

        group_metrics.append({
            'group_type': group_col,
            'group_value': group_val,
            'rows': len(subset),
            'R2': r2_g,
            'MAE': mae_g,
            'RMSE': rmse_g,
            'bias': bias_g
        })

# Sort by MAE worst first
group_metrics.sort(key=lambda x: x['MAE'], reverse=True)

print("Worst 5 groups (by MAE):")
for m in group_metrics[:5]:
    print("  " + m['group_type'] + "=" + str(m['group_value']) + ": MAE=" + str(round(m['MAE'], 4)) + ", R2=" + str(round(m['R2'], 3)))

# ============================================================================
# SAVE METRICS
# ============================================================================
print("\nSaving metrics...\n")

overall_df = pd.DataFrame({
    'metric': ['rows', 'R2', 'MAE', 'RMSE', 'bias', 'pred_min', 'pred_max', 'target_min', 'target_max', 'OOB_count', 'OOB_pct'],
    'value': [total_rows, r2, mae, rmse, bias, all_preds.min(), all_preds.max(), all_targets.min(), all_targets.max(), oob_count, oob_pct]
})

overall_df.to_csv("outputs/external_datasets/oxford_model_on_lg_metrics.csv", index=False)

pd.DataFrame(group_metrics).to_csv("outputs/external_datasets/oxford_model_on_lg_by_group.csv", index=False)

print("Saved: outputs/external_datasets/oxford_model_on_lg_metrics.csv")
print("Saved: outputs/external_datasets/oxford_model_on_lg_by_group.csv")

# ============================================================================
# DECISION
# ============================================================================
print("\nMaking decision...")

if r2 > 0.8:
    decision = "GENERALIZES_ACCEPTABLY"
    reason = "R2 > 0.8, acceptable generalization to LG"
elif r2 > 0.5:
    decision = "DOMAIN_SHIFT_DEGRADES"
    reason = "0.5 < R2 < 0.8, domain shift evident but functional"
else:
    decision = "FAILS_EXTERNAL_GENERALIZATION"
    reason = "R2 < 0.5, model fails on external domain"

# ============================================================================
# SAVE SUMMARY
# ============================================================================
with open("outputs/external_datasets/oxford_model_on_lg_summary.md", 'w') as f:
    f.write("# Oxford Model Evaluation on LG Clean_All_Valid\n\n")
    f.write("## Overall Results\n\n")
    f.write("- Rows evaluated: " + str(total_rows) + "\n")
    f.write("- R2: " + str(round(r2, 4)) + "\n")
    f.write("- MAE: " + str(round(mae, 4)) + "\n")
    f.write("- RMSE: " + str(round(rmse, 4)) + "\n")
    f.write("- Bias: " + str(round(bias, 4)) + "\n")
    f.write("- OOB predictions: " + str(oob_count) + " (" + str(round(oob_pct, 1)) + "%)\n\n")

    f.write("## Best Performing Groups\n\n")
    best_groups = sorted(group_metrics, key=lambda x: x['MAE'])[:3]
    for m in best_groups:
        f.write("- " + m['group_type'] + "=" + str(m['group_value']) + ": MAE=" + str(round(m['MAE'], 4)) + ", R2=" + str(round(m['R2'], 3)) + "\n")

    f.write("\n## Worst Performing Groups\n\n")
    worst_groups = sorted(group_metrics, key=lambda x: x['MAE'], reverse=True)[:3]
    for m in worst_groups:
        f.write("- " + m['group_type'] + "=" + str(m['group_value']) + ": MAE=" + str(round(m['MAE'], 4)) + ", R2=" + str(round(m['R2'], 3)) + "\n")

    f.write("\n## Interpretation\n\n")
    f.write("**" + decision + "**\n\n")
    f.write("Reason: " + reason + "\n\n")
    if oob_pct > 5:
        f.write("⚠️ Warning: " + str(round(oob_pct, 1)) + "% of predictions outside [0,1] bounds\n")

print("Saved: outputs/external_datasets/oxford_model_on_lg_summary.md\n")

# ============================================================================
# FINAL REPORT
# ============================================================================
print("=" * 70)
print("EVALUATION SUMMARY")
print("=" * 70)
print("\nRows evaluated: " + str(total_rows))
print("Overall R2: " + str(round(r2, 4)))
print("Overall MAE: " + str(round(mae, 4)))
print("Overall RMSE: " + str(round(rmse, 4)))
print("Decision: " + decision)
print()
