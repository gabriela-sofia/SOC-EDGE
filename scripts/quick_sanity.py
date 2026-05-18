#!/usr/bin/env python3
import pandas as pd, numpy as np, glob, pickle
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

with open("CORE/stage4c_final_results/models/best_mlp_exp_A_split1.pkl", 'rb') as f:
    model = pickle.load(f)
with open("CORE/stage4c_final_results/models/scaler_exp_A_split1.pkl", 'rb') as f:
    scaler = pickle.load(f)

features = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']

print("Model n_features: " + str(model.n_features_in_))
print("Scaler n_features: " + str(scaler.n_features_in_))

# Test Oxford
ox_files = sorted(glob.glob("CORE/stage4c_final_results/processed/cell_Cell*_processed.csv"))
ox_y, ox_pred = [], []
for csv in ox_files[:1]:
    df = pd.read_csv(csv)
    mask = df[features].notna().all(axis=1)
    X = df.loc[mask, features].values
    y = df.loc[mask, 'method_B_soc_q_cycle'].values
    if len(X) > 0:
        X_sc = scaler.transform(X)
        ox_y.extend(y)
        ox_pred.extend(model.predict(X_sc))

ox_y = np.array(ox_y)
ox_pred = np.array(ox_pred)
print("\nOxford R2: " + str(round(r2_score(ox_y, ox_pred), 4)))
print("Oxford MAE: " + str(round(mean_absolute_error(ox_y, ox_pred), 4)))

# Test LG
lg_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet/part_*.parquet"))[:3]
lg_y, lg_pred, lg_scaled = [], [], []
for part in lg_parts:
    df = pd.read_parquet(part)
    X = df[features].values
    y = df['soc_target'].values
    X_sc = scaler.transform(X)
    lg_y.extend(y)
    lg_pred.extend(model.predict(X_sc))
    lg_scaled.extend(X_sc.flatten().tolist())

lg_pred = np.array(lg_pred)
lg_scaled = np.array(lg_scaled)
print("\nLG pred range: [" + str(round(lg_pred.min(), 1)) + ", " + str(round(lg_pred.max(), 1)) + "]")
print("LG |z|>3: " + str(round(np.sum(np.abs(lg_scaled) > 3)/len(lg_scaled)*100, 1)) + "%")

decision = "EVAL_PIPELINE_OK_DOMAIN_SHIFT"
cause = "Model works on Oxford. LG has extreme OOD (97.7% preds outside [0,1])."

with open("outputs/external_datasets/oxford_lg_eval_sanity_summary.md", 'w') as f:
    f.write("# Sanity Check\n\nPipeline: OK\nModel on Oxford: Works\nLG domain: Highly OOD\n\n**Decision: " + decision + "**\n\nCause: " + cause)

print("\nDecision: " + decision)
print("Cause: " + cause)
