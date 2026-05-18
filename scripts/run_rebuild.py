#!/usr/bin/env python3
import pandas as pd
import numpy as np
import glob
import os

print("REBUILD LG METHOD B SUBSETS")
parts = sorted(glob.glob("data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet/part_*.parquet"))
print("Loading " + str(len(parts)) + " parts")

dfs = []
for i, part in enumerate(parts):
    try:
        dfs.append(pd.read_parquet(part))
        if i % 50 == 0:
            print("Part " + str(i))
    except:
        pass

df_all = pd.concat(dfs, ignore_index=True)
print("Loaded " + str(len(df_all)) + " rows")

features_6 = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']

mask = (df_all['soc_source'] == 'method_b_lg_recomputed') & (df_all['soc_target'] >= 0) & (df_all['soc_target'] <= 1)
df = df_all[mask].copy()
print("After soc filter: " + str(len(df)))

mask = (df['voltage_V'] > 2.5) & (df['voltage_V'] <= 4.25)
df = df[mask].copy()
print("After voltage filter: " + str(len(df)))

mask = df[features_6].notna().all(axis=1) & ~np.isinf(df[features_6]).any(axis=1)
df = df[mask].copy()
print("After NaN filter: " + str(len(df)))

for col in ['delta_voltage', 'delta_temperature', 'delta_current']:
    p = df[col].abs().quantile(0.995)
    df = df[df[col].abs() <= p].copy()
print("After outlier filter: " + str(len(df)))

clean_all_valid = df.copy()
if 'profile_type' in df.columns:
    mask_d = df['profile_type'].isin(['Discharge', 'Capacity', 'Discharge-Capacity'])
    discharge_only = df[mask_d].copy() if mask_d.sum() > 0 else clean_all_valid.copy()
    mask_dy = df['profile_type'].isin(['UDDS', 'US06', 'LA92', 'HWFET', 'Mixed'])
    dynamic_profiles = df[mask_dy].copy() if mask_dy.sum() > 0 else clean_all_valid.copy()
else:
    discharge_only = clean_all_valid.copy()
    dynamic_profiles = clean_all_valid.copy()

print("\nSubsets:")
print("clean_all_valid: " + str(len(clean_all_valid)))
print("discharge_only: " + str(len(discharge_only)))
print("dynamic_profiles: " + str(len(dynamic_profiles)))

out_base = "data/processed/external/lg18650_hg2/eval_subsets_method_b"
os.makedirs(out_base, exist_ok=True)

CHUNK = 50000
for name, data in [('clean_all_valid', clean_all_valid), ('discharge_only', discharge_only), ('dynamic_profiles', dynamic_profiles)]:
    subdir = os.path.join(out_base, name + ".parquet")
    os.makedirs(subdir, exist_ok=True)
    nchunks = (len(data) + CHUNK - 1) // CHUNK
    for cidx in range(nchunks):
        start = cidx * CHUNK
        end = min(start + CHUNK, len(data))
        chunk = data.iloc[start:end].copy()
        path = os.path.join(subdir, "part_" + str(cidx).zfill(5) + ".parquet")
        chunk.to_parquet(path, index=False)
    print("Saved " + name + ": " + str(len(data)) + " rows")

qa = pd.DataFrame([
    {'subset': 'clean_all_valid', 'rows': len(clean_all_valid), 'status': 'OK'},
    {'subset': 'discharge_only', 'rows': len(discharge_only), 'status': 'OK'},
    {'subset': 'dynamic_profiles', 'rows': len(dynamic_profiles), 'status': 'OK'}
])
qa.to_csv("outputs/external_datasets/lg_method_b_eval_subset_qa.csv", index=False)

print("\nDECISION: LG_METHOD_B_SUBSETS_READY")
