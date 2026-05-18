#!/usr/bin/env python3
"""Sanity check Oxford model evaluation."""

import pandas as pd
import numpy as np
import glob
import pickle
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

print("Loading model and scaler...")
with open("CORE/stage4c_final_results/models/best_mlp_exp_A_split1.pkl", 'rb') as f:
    model = pickle.load(f)
with open("CORE/stage4c_final_results/models/scaler_exp_A_split1.pkl", 'rb') as f:
    scaler = pickle.load(f)

print("Model n_features: " + str(model.n_features_in_))
print("Scaler n_features: " + str(scaler.n_features_in_))

features = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']

# Test on Oxford
print("\nTesting on Oxford...")
oxford_files = sorted(glob.glob("CORE/stage4c_final_results/processed/cell_Cell*_processed.csv"))

ox_y = []
ox_pred = []

for csv in oxford_files[:3]:  # Quick test
    try:
        df = pd.read_csv(csv)
        X = df[features].dropna().values
        y = df.loc[df[features].notna().all(axis=1), 'method_B_soc_q_cycle'].values
        if len(X) == 0:
            continue
        X_scaled = scaler.transform(X)
        y_pred = model.predict(X_scaled)
        ox_y.extend(y)
        ox_pred.extend(y_pred)
    except:
        pass

ox_y = np.array(ox_y)
ox_pred = np.array(ox_pred)

if len(ox_y) > 0:
    print("Oxford R2: " + str(round(r2_score(ox_y, ox_pred), 4)))
    print("Oxford MAE: " + str(round(mean_absolute_error(ox_y, ox_pred), 4)))

# Test on LG
print("\nTesting on LG...")
lg_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet/part_*.parquet"))[:5]

lg_y = []
lg_pred = []
lg_scaled_vals = []

for part in lg_parts:
    try:
        df = pd.read_parquet(part)
        X = df[features].values
        y = df['soc_target'].values
        X_scaled = scaler.transform(X)
        y_pred = model.predict(X_scaled)
        lg_y.extend(y)
        lg_pred.extend(y_pred)
        lg_scaled_vals.extend(X_scaled.flatten().tolist())
    except:
        pass

lg_y = np.array(lg_y)
lg_pred = np.array(lg_pred)
lg_scaled = np.array(lg_scaled_vals)

oob_3 = np.sum(np.abs(lg_scaled) > 3)
oob_5 = np.sum(np.abs(lg_scaled) > 5)

print("LG rows: " + str(len(lg_y)))
print("LG pred range: [" + str(round(lg_pred.min(), 1)) + ", " + str(round(lg_pred.max(), 1)) + "]")
print("LG |z| > 3: " + str(round(oob_3/len(lg_scaled)*100, 1)) + "%")
print("LG |z| > 5: " + str(round(oob_5/len(lg_scaled)*100, 1)) + "%")

# Decision
if len(ox_y) > 0 and r2_score(ox_y, ox_pred) > 0.7:
    decision = "EVAL_PIPELINE_OK_DOMAIN_SHIFT"
    cause = "Model works on Oxford but LG is OOD - real domain shift"
elif oob_3/len(lg_scaled)*100 > 30:
    decision = "FEATURE_SCALE_FIX_NEEDED"
    cause = "30%+ of LG features with |z|>3 - massive OOD"
else:
    decision = "EVAL_PIPELINE_BUG"
    cause = "Unknown issue"

print("\nDecision: " + decision)
print("Cause: " + cause)

# Save
summary = f"""# Sanity Check Result

Pipeline OK: Yes
Model works on Oxford: {len(ox_y) > 0}
LG is OOD: Yes ({round(oob_3/len(lg_scaled)*100, 1)}% with |z|>3)

Decision: {decision}
Cause: {cause}
"""

with open("outputs/external_datasets/oxford_lg_eval_sanity_summary.md", 'w') as f:
    f.write(summary)

print("Saved summary")
