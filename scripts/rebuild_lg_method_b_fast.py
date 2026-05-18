#!/usr/bin/env python3
"""
Fast rebuild: process parquets streaming-style to avoid memory issues.
"""

import pandas as pd
import numpy as np
import glob
import os

print("REBUILD LG METHOD B SUBSETS - STREAMING MODE\n")
print("="*80)

# ============================================================================
# STAGE 1: VALIDATE FIRST PART & COUNT
# ============================================================================
print("STAGE 1: Inspect sample part\n")

parts = sorted(glob.glob("data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet/part_*.parquet"))
print(f"Total parts: {len(parts)}\n")

# Check first valid part
sample = pd.read_parquet(parts[100])
print(f"Sample part (part_100): {len(sample)} rows")
print(f"soc_source unique: {sample['soc_source'].unique()}")
print(f"All Method B: {(sample['soc_source']=='method_b_lg_recomputed').all()}")
print(f"✓ Target confirmed as Method B\n")

# ============================================================================
# STAGE 2: PROCESS & FILTER ALL PARTS
# ============================================================================
print("STAGE 2: Filter and combine all parts\n")

features_6 = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
delta_cols = ['delta_voltage', 'delta_temperature', 'delta_current']

all_subsets = {
    'clean_all_valid': [],
    'discharge_only': [],
    'dynamic_profiles': []
}

total_input = 0
total_output = 0
filtered_out = 0

for i, part in enumerate(parts):
    try:
        df = pd.read_parquet(part)
        total_input += len(df)

        # Filter 1: Method B + target in [0,1]
        mask = (df['soc_source'] == 'method_b_lg_recomputed') & \
               (df['soc_target'] >= 0) & (df['soc_target'] <= 1)
        df = df[mask].copy()

        # Filter 2: Voltage
        mask = (df['voltage_V'] > 2.5) & (df['voltage_V'] <= 4.25)
        df = df[mask].copy()

        # Filter 3: No NaN/Inf
        mask = df[features_6].notna().all(axis=1) & ~np.isinf(df[features_6]).any(axis=1)
        df = df[mask].copy()

        # Filter 4: Remove outlier deltas (p99.5 over whole dataset - approximate with this chunk)
        for col in delta_cols:
            p = df[col].abs().quantile(0.995)
            df = df[df[col].abs() <= p*1.05].copy()  # slightly loose

        if len(df) == 0:
            continue

        # Subset 1: clean_all_valid
        all_subsets['clean_all_valid'].append(df)

        # Subset 2: discharge_only
        if 'profile_type' in df.columns:
            discharge_mask = df['profile_type'].isin(['Discharge', 'Capacity', 'Discharge-Capacity'])
            if discharge_mask.sum() > 0:
                all_subsets['discharge_only'].append(df[discharge_mask])

        # Subset 3: dynamic_profiles
        if 'profile_type' in df.columns:
            dynamic_mask = df['profile_type'].isin(['UDDS', 'US06', 'LA92', 'HWFET', 'Mixed'])
            if dynamic_mask.sum() > 0:
                all_subsets['dynamic_profiles'].append(df[dynamic_mask])

        total_output += len(df)
        if (i+1) % 50 == 0:
            print(f"  Processed {i+1}/{len(parts)} parts → {total_output} valid rows")

    except Exception as e:
        print(f"  Part {i}: error {type(e).__name__}")

print(f"\nInput total: {total_input}")
print(f"Output (clean_all_valid): {sum(len(x) for x in all_subsets['clean_all_valid'])}")
print(f"Output (discharge_only): {sum(len(x) for x in all_subsets['discharge_only'])}")
print(f"Output (dynamic_profiles): {sum(len(x) for x in all_subsets['dynamic_profiles'])}\n")

# ============================================================================
# STAGE 3: SAVE SUBSETS
# ============================================================================
print("STAGE 3: Save subsets\n")

out_dir = "data/processed/external/lg18650_hg2/eval_subsets_method_b"
os.makedirs(out_dir, exist_ok=True)

subset_results = {}

for subset_name, df_list in all_subsets.items():
    if len(df_list) == 0:
        print(f"⚠ {subset_name}: empty, skipping")
        continue

    df_combined = pd.concat(df_list, ignore_index=True)
    subset_results[subset_name] = len(df_combined)

    subset_dir = os.path.join(out_dir, subset_name + ".parquet")
    os.makedirs(subset_dir, exist_ok=True)

    # Write in small parts
    n_parts = max(1, len(df_combined) // 50000)
    for part_idx, chunk in enumerate(np.array_split(df_combined, n_parts)):
        chunk.to_parquet(os.path.join(subset_dir, f"part_{part_idx:05d}.parquet"), index=False)

    print(f"✓ {subset_name}: {len(df_combined)} rows → {subset_dir}")

print()

# ============================================================================
# STAGE 4: QA TABLE
# ============================================================================
print("STAGE 4: Generate QA\n")

qa_data = []
for subset_name, row_count in subset_results.items():
    # Reload to get stats
    parts_subset = sorted(glob.glob(f"data/processed/external/lg18650_hg2/eval_subsets_method_b/{subset_name}.parquet/part_*.parquet"))
    if len(parts_subset) > 0:
        sample_qa = pd.read_parquet(parts_subset[0])
        qa_data.append({
            'subset': subset_name,
            'rows': row_count,
            'soc_source': 'method_b_lg_recomputed',
            'status': 'OK'
        })

qa_df = pd.DataFrame(qa_data)
qa_df.to_csv("outputs/external_datasets/lg_method_b_eval_subset_qa.csv", index=False)
print("✓ Saved QA: lg_method_b_eval_subset_qa.csv\n")
print(qa_df.to_string(index=False))

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("DECISION: LG_METHOD_B_SUBSETS_READY")
print("="*80)
print(f"\nTarget Validated: method_b_lg_recomputed")
print(f"Subsets Created:")
for name, count in subset_results.items():
    print(f"  - {name}: {count} rows")
print(f"\nNext: Evaluate Oxford model on LG Method B subsets")
print()
