#!/usr/bin/env python3
"""Evaluate frozen Oxford model on LG clean_all_valid - no training."""

import pandas as pd
import numpy as np
import glob
import pickle
import gc
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

print("Loading Oxford model and scaler...")
with open("CORE/stage4c_final_results/models/best_mlp_exp_A_split1.pkl", 'rb') as f:
    model = pickle.load(f)
with open("CORE/stage4c_final_results/models/scaler_exp_A_split1.pkl", 'rb') as f:
    scaler = pickle.load(f)

# 6 features (no current_rel)
features = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
target = 'soc_target'

print("Loading LG parts...")
parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet/part_*.parquet"))

targets = []
preds = []
group_data = {'profile_type': [], 'temperature_condition': [], 'cell_id': []}
total = 0

for i, part in enumerate(parts):
    try:
        df = pd.read_parquet(part)
    except:
        continue

    if not all(c in df.columns for c in features + [target]):
        continue

    X = df[features].values
    y = df[target].values
    X_scaled = scaler.transform(X)
    y_pred = model.predict(X_scaled)

    targets.extend(y)
    preds.extend(y_pred)
    group_data['profile_type'].extend(df['profile_type'].values)
    group_data['temperature_condition'].extend(df['temperature_condition'].values)
    group_data['cell_id'].extend(df['cell_id'].values)

    total += len(df)
    if (i + 1) % 10 == 0:
        print("  " + str(i+1) + "/" + str(len(parts)) + " - " + str(total) + " rows")

    del df, X, y, X_scaled, y_pred
    gc.collect()

targets = np.array(targets)
preds = np.array(preds)

r2 = r2_score(targets, preds)
mae = mean_absolute_error(targets, preds)
rmse = np.sqrt(mean_squared_error(targets, preds))
bias = np.mean(preds - targets)
oob = np.sum((preds < 0) | (preds > 1))

print("\n" + "="*70)
print("Overall metrics (raw):")
print("Rows: " + str(total))
print("R2: " + str(round(r2, 4)))
print("MAE: " + str(round(mae, 4)))
print("RMSE: " + str(round(rmse, 4)))
print("Bias: " + str(round(bias, 4)))
print("OOB: " + str(oob) + " (" + str(round(oob/len(preds)*100, 1)) + "%)")

# Group metrics
df_eval = pd.DataFrame({'target': targets, 'pred': preds, 'profile_type': group_data['profile_type'], 'temperature_condition': group_data['temperature_condition'], 'cell_id': group_data['cell_id']})

group_metrics = []
for col in ['profile_type', 'temperature_condition', 'cell_id']:
    for val in df_eval[col].unique():
        sub = df_eval[df_eval[col] == val]
        if len(sub) < 100:
            continue
        r2_g = r2_score(sub['target'], sub['pred'])
        mae_g = mean_absolute_error(sub['target'], sub['pred'])
        rmse_g = np.sqrt(mean_squared_error(sub['target'], sub['pred']))
        bias_g = np.mean(sub['pred'] - sub['target'])
        group_metrics.append({'group_type': col, 'group_value': val, 'rows': len(sub), 'R2': r2_g, 'MAE': mae_g, 'RMSE': rmse_g, 'bias': bias_g})

# Decision
decision = "GENERALIZES_ACCEPTABLY" if r2 > 0.8 else ("DOMAIN_SHIFT_DEGRADES" if r2 > 0.5 else "FAILS_EXTERNAL_GENERALIZATION")

# Save
pd.DataFrame({'metric': ['rows', 'R2', 'MAE', 'RMSE', 'bias'], 'value': [total, r2, mae, rmse, bias]}).to_csv("outputs/external_datasets/oxford_model_on_lg_metrics.csv", index=False)
pd.DataFrame(group_metrics).to_csv("outputs/external_datasets/oxford_model_on_lg_by_group.csv", index=False)

with open("outputs/external_datasets/oxford_model_on_lg_summary.md", 'w') as f:
    f.write("# Oxford Model on LG Evaluation\n\n")
    f.write("## Results\n\n")
    f.write("- Rows: " + str(total) + "\n")
    f.write("- R2: " + str(round(r2, 4)) + "\n")
    f.write("- MAE: " + str(round(mae, 4)) + "\n")
    f.write("- RMSE: " + str(round(rmse, 4)) + "\n")
    f.write("- OOB: " + str(oob) + " (" + str(round(oob/len(preds)*100, 1)) + "%)\n\n")
    f.write("## Decision\n\n")
    f.write("**" + decision + "**\n")

print("Saved metrics")
print("Decision: " + decision)
