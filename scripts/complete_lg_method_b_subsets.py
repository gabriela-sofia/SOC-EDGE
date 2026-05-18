#!/usr/bin/env python3
"""
Complete the rebuild by creating discharge_only and dynamic_profiles from already-saved clean_all_valid.
"""

import pandas as pd
import glob
import os

print("COMPLETE LG METHOD B SUBSETS (from clean_all_valid)")
print("="*80 + "\n")

# Load clean_all_valid from saved parquets
print("STEP 1: Load clean_all_valid from saved parquets")
print("-"*80 + "\n")

parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_*.parquet"))
print("Loading " + str(len(parts)) + " parts...")

dfs = []
for i, part in enumerate(parts):
    try:
        dfs.append(pd.read_parquet(part))
        if (i+1) % 10 == 0:
            print("  Part " + str(i+1))
    except Exception as e:
        print("  Part " + str(i) + ": error - " + str(type(e).__name__))

clean_all_valid = pd.concat(dfs, ignore_index=True)
print("Loaded " + str(len(clean_all_valid)) + " rows\n")

# Create subsets
print("STEP 2: Create discharge_only and dynamic_profiles")
print("-"*80 + "\n")

if 'profile_type' in clean_all_valid.columns:
    discharge_mask = clean_all_valid['profile_type'].isin(['Discharge', 'Capacity', 'Discharge-Capacity'])
    discharge_only = clean_all_valid[discharge_mask].copy()
    print("discharge_only: " + str(len(discharge_only)) + " rows")

    dynamic_mask = clean_all_valid['profile_type'].isin(['UDDS', 'US06', 'LA92', 'HWFET', 'Mixed'])
    dynamic_profiles = clean_all_valid[dynamic_mask].copy()
    print("dynamic_profiles: " + str(len(dynamic_profiles)) + " rows\n")
else:
    print("profile_type not found, using clean_all_valid for both")
    discharge_only = clean_all_valid.copy()
    dynamic_profiles = clean_all_valid.copy()

# Save
print("STEP 3: Save subsets")
print("-"*80 + "\n")

out_base = "data/processed/external/lg18650_hg2/eval_subsets_method_b"
CHUNK = 50000

for name, data in [('discharge_only', discharge_only), ('dynamic_profiles', dynamic_profiles)]:
    subdir = os.path.join(out_base, name + ".parquet")
    os.makedirs(subdir, exist_ok=True)

    nchunks = (len(data) + CHUNK - 1) // CHUNK
    for cidx in range(nchunks):
        start = cidx * CHUNK
        end = min(start + CHUNK, len(data))
        chunk = data.iloc[start:end].copy()
        path = os.path.join(subdir, "part_" + str(cidx).zfill(5) + ".parquet")
        chunk.to_parquet(path, index=False)

    print("Saved " + name + ": " + str(len(data)) + " rows -> " + str(nchunks) + " parts")

print("\nDONE: All 3 subsets now saved")
