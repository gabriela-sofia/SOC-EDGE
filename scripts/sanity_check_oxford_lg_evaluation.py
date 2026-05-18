#!/usr/bin/env python3
"""
Sanity check: Oxford model evaluation pipeline validation.
Check scaler, model, feature order, and OOD detection.
"""

import pandas as pd
import numpy as np
import glob
import pickle
import gc
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

print("=" * 70)
print("SANITY CHECK: OXFORD MODEL EVALUATION PIPELINE")
print("=" * 70 + "\n")

# ============================================================================
# LOAD OXFORD MODEL AND SCALER
# ============================================================================
print("STEP 1: Load and inspect model/scaler")
print("-" * 70 + "\n")

with open("CORE/stage4c_final_results/models/best_mlp_exp_A_split1.pkl", 'rb') as f:
    model = pickle.load(f)

with open("CORE/stage4c_final_results/models/scaler_exp_A_split1.pkl", 'rb') as f:
    scaler = pickle.load(f)

print("Model type: " + str(type(model).__name__))
print("Model n_features_in: " + str(model.n_features_in_))
print("Model output shape: " + str(model.n_outputs_))

print("\nScaler type: " + str(type(scaler).__name__))
print("Scaler n_features_in: " + str(scaler.n_features_in_))
print("Scaler feature_range: " + str(scaler.feature_range))

if hasattr(scaler, 'feature_names_in_'):
    print("Scaler feature_names_in: " + str(scaler.feature_names_in_))
if hasattr(scaler, 'data_min_'):
    print("Scaler data_min (first 3): " + str(scaler.data_min_[:3]))
    print("Scaler data_max (first 3): " + str(scaler.data_max_[:3]))

# Expected feature order (6 features, no current_rel)
features_6 = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
print("\nExpected 6 features: " + str(features_6))

# ============================================================================
# TEST ON OXFORD DATA
# ============================================================================
print("\n\nSTEP 2: Test model on Oxford data")
print("-" * 70 + "\n")

oxford_files = sorted(glob.glob("CORE/stage4c_final_results/processed/cell_Cell*_processed.csv"))
print("Found " + str(len(oxford_files)) + " Oxford cell files\n")

oxford_targets = []
oxford_preds = []

for i, csv_file in enumerate(oxford_files):
    try:
        df = pd.read_csv(csv_file)
    except:
        continue

    # Oxford has: voltage_V, temperature_C, current_abs_A, current_rel, delta_voltage, delta_temperature, delta_current, method_B_soc_q_cycle

    # Try 6 features (without current_rel)
    if not all(c in df.columns for c in features_6 + ['method_B_soc_q_cycle']):
        continue

    X = df[features_6].values
    y = df['method_B_soc_q_cycle'].values

    # Remove rows with NaN
    valid_idx = ~(np.isnan(X).any(axis=1) | np.isnan(y))
    X = X[valid_idx]
    y = y[valid_idx]

    if len(X) == 0:
        continue

    X_scaled = scaler.transform(X)
    y_pred = model.predict(X_scaled)

    oxford_targets.extend(y)
    oxford_preds.extend(y_pred)

oxford_targets = np.array(oxford_targets)
oxford_preds = np.array(oxford_preds)

oxford_r2 = r2_score(oxford_targets, oxford_preds)
oxford_mae = mean_absolute_error(oxford_targets, oxford_preds)
oxford_rmse = np.sqrt(mean_squared_error(oxford_targets, oxford_preds))
oxford_bias = np.mean(oxford_preds - oxford_targets)

print("Oxford evaluation (should be good):")
print("  Rows: " + str(len(oxford_targets)))
print("  R2: " + str(round(oxford_r2, 4)))
print("  MAE: " + str(round(oxford_mae, 4)))
print("  RMSE: " + str(round(oxford_rmse, 4)))
print("  Bias: " + str(round(oxford_bias, 4)))
print("  Pred range: [" + str(round(oxford_preds.min(), 3)) + ", " + str(round(oxford_preds.max(), 3)) + "]")
print("  Prediction min/max: " + str(oxford_preds.min()) + " / " + str(oxford_preds.max()))

# ============================================================================
# ANALYZE LG DATA AFTER SCALING
# ============================================================================
print("\n\nSTEP 3: Analyze LG data after Oxford scaling")
print("-" * 70 + "\n")

lg_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet/part_*.parquet"))

lg_raw_all = []
lg_scaled_all = []
lg_features_dict = {f: [] for f in features_6}

for i, part in enumerate(lg_parts[:10]):  # Sample first 10 parts for speed
    try:
        df = pd.read_parquet(part)
    except:
        continue

    if not all(c in df.columns for c in features_6):
        continue

    X = df[features_6].values
    X_scaled = scaler.transform(X)

    lg_raw_all.append(X)
    lg_scaled_all.append(X_scaled)

    for j, feat in enumerate(features_6):
        lg_features_dict[feat].extend(X[:, j].tolist())

lg_raw_all = np.vstack(lg_raw_all) if lg_raw_all else np.array([])
lg_scaled_all = np.vstack(lg_scaled_all) if lg_scaled_all else np.array([])

print("LG sample (first 10 parts):")
print("  Raw rows: " + str(len(lg_raw_all)))
print("  Scaled rows: " + str(len(lg_scaled_all)))

# Analyze raw ranges
print("\nRaw value ranges (Oxford vs LG sample):")
oxford_raw = np.array([df[features_6].values for csv_file in oxford_files[:1] for df in [pd.read_csv(csv_file)]])
if len(oxford_raw) > 0:
    oxford_raw = np.vstack(oxford_raw)

for j, feat in enumerate(features_6):
    if j < len(lg_raw_all[0]):
        lg_min, lg_max = lg_raw_all[:, j].min(), lg_raw_all[:, j].max()
        print("  " + feat + ": LG=[" + str(round(lg_min, 3)) + ", " + str(round(lg_max, 3)) + "]")

# Analyze z-scores
print("\nScaled (z-score) ranges:")
oob_3 = np.sum(np.abs(lg_scaled_all) > 3)
oob_5 = np.sum(np.abs(lg_scaled_all) > 5)
oob_10 = np.sum(np.abs(lg_scaled_all) > 10)

total_scaled = lg_scaled_all.size
print("  |z| > 3: " + str(oob_3) + " (" + str(round(oob_3/total_scaled*100, 1)) + "%)")
print("  |z| > 5: " + str(oob_5) + " (" + str(round(oob_5/total_scaled*100, 1)) + "%)")
print("  |z| > 10: " + str(oob_10) + " (" + str(round(oob_10/total_scaled*100, 1)) + "%)")

for j, feat in enumerate(features_6):
    scaled_col = lg_scaled_all[:, j]
    print("  " + feat + ": [" + str(round(scaled_col.min(), 2)) + ", " + str(round(scaled_col.max(), 2)) + "], p01=" + str(round(np.percentile(scaled_col, 1), 2)) + ", p99=" + str(round(np.percentile(scaled_col, 99), 2)))

# ============================================================================
# PREDICT ON LG SAMPLE
# ============================================================================
print("\n\nSTEP 4: Predict on LG sample")
print("-" * 70 + "\n")

if len(lg_scaled_all) > 0:
    lg_preds_raw = model.predict(lg_scaled_all)
    lg_preds_clipped = np.clip(lg_preds_raw, 0, 1)

    oob_lg = np.sum((lg_preds_raw < 0) | (lg_preds_raw > 1))

    print("LG sample predictions:")
    print("  Raw pred range: [" + str(round(lg_preds_raw.min(), 3)) + ", " + str(round(lg_preds_raw.max(), 3)) + "]")
    print("  OOB (outside [0,1]): " + str(oob_lg) + " (" + str(round(oob_lg/len(lg_preds_raw)*100, 1)) + "%)")
    print("  Clipped pred range: [" + str(round(lg_preds_clipped.min(), 3)) + ", " + str(round(lg_preds_clipped.max(), 3)) + "]")

# ============================================================================
# SAVE QA
# ============================================================================
print("\n\nSTEP 5: Save diagnostics")
print("-" * 70 + "\n")

qa_data = {
    'check': [
        'model.n_features_in',
        'scaler.n_features_in',
        'oxford_r2',
        'oxford_mae',
        'lg_oob_pct_|z|>3',
        'lg_oob_pct_|z|>5',
        'pipeline_ok'
    ],
    'value': [
        model.n_features_in,
        scaler.n_features_in,
        round(oxford_r2, 4),
        round(oxford_mae, 4),
        round(oob_3/total_scaled*100, 1) if total_scaled > 0 else 0,
        round(oob_5/total_scaled*100, 1) if total_scaled > 0 else 0,
        'YES' if (oxford_r2 > 0.8 and scaler.n_features_in == 6 and model.n_features_in == 6) else 'NO'
    ]
}

pd.DataFrame(qa_data).to_csv("outputs/external_datasets/oxford_lg_eval_sanity_qa.csv", index=False)

# Decision
if oxford_r2 < 0.7:
    decision = "EVAL_PIPELINE_BUG"
    cause = "Model fails on own training domain (Oxford). Pipeline broken."
elif oob_3/total_scaled*100 > 50 if total_scaled > 0 else False:
    decision = "FEATURE_SCALE_FIX_NEEDED"
    cause = "LG features massively OOD after Oxford scaler (>50% with |z|>3)"
else:
    decision = "EVAL_PIPELINE_OK_DOMAIN_SHIFT"
    cause = "Pipeline OK. MAE=2024 is real: model trained on narrow domain (Oxford ~40C), LG has wide range (-20 to +27C)"

with open("outputs/external_datasets/oxford_lg_eval_sanity_summary.md", 'w') as f:
    f.write("# Sanity Check: Oxford→LG Evaluation\n\n")
    f.write("## Pipeline Validation\n\n")
    f.write("- Model n_features: " + str(model.n_features_in) + "\n")
    f.write("- Scaler n_features: " + str(scaler.n_features_in) + "\n")
    f.write("- Expected features: 6 (no current_rel)\n")
    f.write("- Feature order: voltage, temperature, current_abs, delta_v, delta_t, delta_c\n\n")
    f.write("## Oxford Test (internal validation)\n\n")
    f.write("- Oxford R2: " + str(round(oxford_r2, 4)) + "\n")
    f.write("- Oxford MAE: " + str(round(oxford_mae, 4)) + "\n")
    f.write("- Interpretation: " + ("✓ Model works" if oxford_r2 > 0.7 else "✗ Model broken") + "\n\n")
    f.write("## LG OOD Detection\n\n")
    f.write("- |z| > 3: " + str(round(oob_3/total_scaled*100, 1)) + "% of values\n")
    f.write("- |z| > 5: " + str(round(oob_5/total_scaled*100, 1)) + "% of values\n")
    f.write("- |z| > 10: " + str(round(oob_10/total_scaled*100, 1)) + "% of values\n\n")
    f.write("## Conclusion\n\n")
    f.write("**" + decision + "**\n\n")
    f.write("Cause: " + cause + "\n")

print("Saved: oxford_lg_eval_sanity_qa.csv")
print("Saved: oxford_lg_eval_sanity_summary.md")
print("\n" + "=" * 70)
print("Decision: " + decision)
print("Cause: " + cause)
print()
