#!/usr/bin/env python3
import pandas as pd
import numpy as np
import glob
import os
import shutil

print("REBUILD LG METHOD B SUBSETS - FIXED")
print("="*80 + "\n")

# Load
parts = sorted(glob.glob("data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet/part_*.parquet"))
print("Loading", len(parts), "parts...")
dfs = []
for i, part in enumerate(parts):
    try:
        dfs.append(pd.read_parquet(part))
        if i % 50 == 0:
            print("  Part", i)
    except:
        pass

df_all = pd.concat(dfs, ignore_index=True)
print("Loaded", len(df_all), "rows\n")

# Filter
features_6 = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']

mask = (df_all['soc_source'] == 'method_b_lg_recomputed') & (df_all['soc_target'] >= 0) & (df_all['soc_target'] <= 1)
df = df_all[mask].copy()
print("After soc filter:", len(df))

mask = (df['voltage_V'] > 2.5) & (df['voltage_V'] <= 4.25)
df = df[mask].copy()
print("After voltage filter:", len(df))

mask = df[features_6].notna().all(axis=1) & ~np.isinf(df[features_6]).any(axis=1)
df = df[mask].copy()
print("After NaN/Inf filter:", len(df))

for col in ['delta_voltage', 'delta_temperature', 'delta_current']:
    p = df[col].abs().quantile(0.995)
    df = df[df[col].abs() <= p].copy()
print("After outlier filter:", len(df), "\n")

# Subsets
clean_all_valid = df.copy()
if 'profile_type' in df.columns:
    mask_d = df['profile_type'].isin(['Discharge', 'Capacity', 'Discharge-Capacity'])
    discharge_only = df[mask_d].copy() if mask_d.sum() > 0 else clean_all_valid.copy()
    mask_dy = df['profile_type'].isin(['UDDS', 'US06', 'LA92', 'HWFET', 'Mixed'])
    dynamic_profiles = df[mask_dy].copy() if mask_dy.sum() > 0 else clean_all_valid.copy()
else:
    discharge_only = clean_all_valid.copy()
    dynamic_profiles = clean_all_valid.copy()

print("Subsets created:")
print("  clean_all_valid:", len(clean_all_valid))
print("  discharge_only:", len(discharge_only))
print("  dynamic_profiles:", len(dynamic_profiles), "\n")

# Clean and save
out_base = "data/processed/external/lg18650_hg2/eval_subsets_method_b"
# Create base dir if doesn't exist (don't delete old one due to permissions)
os.makedirs(out_base, exist_ok=True)

CHUNK_SIZE = 50000
for name, subset_df in [('clean_all_valid', clean_all_valid), ('discharge_only', discharge_only), ('dynamic_profiles', dynamic_profiles)]:
    subset_dir = os.path.join(out_base, name + ".parquet")
    os.makedirs(subset_dir, exist_ok=True)
    n_chunks = (len(subset_df) + CHUNK_SIZE - 1) // CHUNK_SIZE
    for chunk_idx in range(n_chunks):
        start = chunk_idx * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, len(subset_df))
        chunk = subset_df.iloc[start:end].copy()
        chunk.to_parquet(os.path.join(subset_dir, "part_" + str(chunk_idx).zfill(5) + ".parquet"), index=False)
    print("Saved", name, ":", len(subset_df), "rows,", n_chunks, "parts")

print()

# QA
qa = pd.DataFrame([
    {'subset': 'clean_all_valid', 'rows': len(clean_all_valid), 'status': 'OK'},
    {'subset': 'discharge_only', 'rows': len(discharge_only), 'status': 'OK'},
    {'subset': 'dynamic_profiles', 'rows': len(dynamic_profiles), 'status': 'OK'}
])
qa.to_csv("outputs/external_datasets/lg_method_b_eval_subset_qa.csv", index=False)
print("QA saved")
print(qa.to_string(index=False))

print("\n" + "="*80)
print("DECISION: LG_METHOD_B_SUBSETS_READY")
print("="*80)
