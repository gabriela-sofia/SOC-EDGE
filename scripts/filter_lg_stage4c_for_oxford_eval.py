#!/usr/bin/env python3
"""
Filter LG Stage 4C for Oxford external evaluation.
Create 3 subsets: clean_all_valid, oxford_overlap_strict, low_current_discharge_dynamic.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import glob
import gc

print("=" * 70)
print("FILTERING LG STAGE 4C FOR OXFORD EVALUATION")
print("=" * 70 + "\n")

# ============================================================================
# LOAD OXFORD STATS
# ============================================================================
print("Loading Oxford distribution stats...")
oxford_qa = pd.read_csv("outputs/external_datasets/oxford_lg_stage4c_distribution_qa.csv")

oxford_stats = {}
for _, row in oxford_qa.iterrows():
    feat = row['feature']
    oxford_stats[feat] = {
        'p01': row['oxford_p01'],
        'p99': row['oxford_p99'],
        'min': row['oxford_min'],
        'max': row['oxford_max'],
        'mean': row['oxford_mean']
    }

print("Oxford stats loaded for " + str(len(oxford_stats)) + " features\n")

# ============================================================================
# COMPUTE LG PERCENTILES FOR ANOMALY DETECTION
# ============================================================================
print("Computing LG percentiles for anomaly detection...")

lg_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet/part_*.parquet"))

# First pass: collect stats
deltas_all = {'delta_voltage': [], 'delta_temperature': [], 'delta_current': []}

for i, part in enumerate(lg_parts):
    try:
        df = pd.read_parquet(part)
        for delta_col in deltas_all:
            if delta_col in df.columns:
                deltas_all[delta_col].extend(df[delta_col].dropna().values.tolist())
    except:
        pass

    if (i + 1) % 50 == 0:
        print("  " + str(i + 1) + "/" + str(len(lg_parts)))

# Compute p99.5 for deltas
delta_p995 = {}
for delta_col in deltas_all:
    vals = np.array(deltas_all[delta_col])
    delta_p995[delta_col] = np.percentile(np.abs(vals), 99.5)

print("Delta p99.5: " + str({k: round(v, 3) for k, v in delta_p995.items()}) + "\n")

# ============================================================================
# SETUP OUTPUT DIRS
# ============================================================================
subsets = {
    'clean_all_valid': Path("data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet"),
    'oxford_overlap_strict': Path("data/processed/external/lg18650_hg2/eval_subsets/oxford_overlap_strict.parquet"),
    'low_current_discharge_dynamic': Path("data/processed/external/lg18650_hg2/eval_subsets/low_current_discharge_dynamic.parquet")
}

for subset_path in subsets.values():
    subset_path.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FILTER AND CREATE SUBSETS
# ============================================================================
print("Filtering and creating subsets...\n")

subset_counts = {
    'clean_all_valid': {'rows': 0, 'files': set(), 'profiles': set(), 'cells': set(), 'part_idx': 0},
    'oxford_overlap_strict': {'rows': 0, 'files': set(), 'profiles': set(), 'cells': set(), 'part_idx': 0},
    'low_current_discharge_dynamic': {'rows': 0, 'files': set(), 'profiles': set(), 'cells': set(), 'part_idx': 0}
}

total_input_rows = 0
total_removed = 0

for part_idx, part in enumerate(lg_parts):
    try:
        df = pd.read_parquet(part)
    except:
        continue

    if len(df) == 0:
        continue

    total_input_rows += len(df)

    # ====================================================================
    # ANOMALY REMOVAL
    # ====================================================================
    initial_rows = len(df)

    # Voltage anomalies
    df = df[~(df['voltage_V'] <= 2.5) & ~(df['voltage_V'] > 4.25)]

    # SOC out of bounds
    df = df[~((df['soc_target'] < 0) | (df['soc_target'] > 1))]

    # Null critical columns
    df = df[df['temperature_C'].notna()]
    df = df[df['current_abs_A'].notna()]

    # Delta null/inf
    for delta_col in ['delta_voltage', 'delta_temperature', 'delta_current']:
        if delta_col in df.columns:
            df = df[df[delta_col].notna()]
            df = df[~np.isinf(df[delta_col])]

    # Delta outliers (abs > p99.5)
    for delta_col in ['delta_voltage', 'delta_temperature', 'delta_current']:
        if delta_col in df.columns and delta_col in delta_p995:
            df = df[np.abs(df[delta_col]) <= delta_p995[delta_col]]

    removed_this_part = initial_rows - len(df)
    total_removed += removed_this_part

    if len(df) == 0:
        continue

    # ====================================================================
    # SUBSET 1: CLEAN_ALL_VALID
    # ====================================================================
    df1 = df.copy()

    # Track metadata
    subset_counts['clean_all_valid']['rows'] += len(df1)
    if 'source_file' in df1.columns:
        subset_counts['clean_all_valid']['files'].update(df1['source_file'].unique())
    if 'profile_type' in df1.columns:
        subset_counts['clean_all_valid']['profiles'].update(df1['profile_type'].unique())
    if 'cell_id' in df1.columns:
        subset_counts['clean_all_valid']['cells'].update(df1['cell_id'].unique())

    df1.to_parquet(
        subsets['clean_all_valid'] / ("part_" + str(subset_counts['clean_all_valid']['part_idx']) + ".parquet"),
        index=False, compression='snappy'
    )
    subset_counts['clean_all_valid']['part_idx'] += 1

    # ====================================================================
    # SUBSET 2: OXFORD_OVERLAP_STRICT
    # ====================================================================
    df2 = df.copy()

    # Filter by Oxford p01-p99 with 10% margin
    for feat in ['voltage_V', 'temperature_C', 'current_abs_A']:
        if feat in df2.columns and feat in oxford_stats:
            p01 = oxford_stats[feat]['p01']
            p99 = oxford_stats[feat]['p99']
            margin = (p99 - p01) * 0.1
            lower = p01 - margin
            upper = p99 + margin
            df2 = df2[(df2[feat] >= lower) & (df2[feat] <= upper)]

    if len(df2) > 0:
        subset_counts['oxford_overlap_strict']['rows'] += len(df2)
        if 'source_file' in df2.columns:
            subset_counts['oxford_overlap_strict']['files'].update(df2['source_file'].unique())
        if 'profile_type' in df2.columns:
            subset_counts['oxford_overlap_strict']['profiles'].update(df2['profile_type'].unique())
        if 'cell_id' in df2.columns:
            subset_counts['oxford_overlap_strict']['cells'].update(df2['cell_id'].unique())

        df2.to_parquet(
            subsets['oxford_overlap_strict'] / ("part_" + str(subset_counts['oxford_overlap_strict']['part_idx']) + ".parquet"),
            index=False, compression='snappy'
        )
        subset_counts['oxford_overlap_strict']['part_idx'] += 1

    # ====================================================================
    # SUBSET 3: LOW_CURRENT_DISCHARGE_DYNAMIC
    # ====================================================================
    df3 = df.copy()

    # Filter by current close to Oxford mean
    if 'current_abs_A' in df3.columns and 'current_abs_A' in oxford_stats:
        oxford_mean = oxford_stats['current_abs_A']['mean']
        oxford_range = oxford_stats['current_abs_A']['p99'] - oxford_stats['current_abs_A']['p01']
        # Allow ±2 std from Oxford mean
        tolerance = oxford_range / 2
        df3 = df3[(df3['current_abs_A'] >= oxford_mean - tolerance) & (df3['current_abs_A'] <= oxford_mean + tolerance)]

    # Filter by profile
    realistic_profiles = ['Discharge', 'Capacity', 'Mixed', 'UDDS', 'US06', 'LA92', 'HWFET']
    if 'profile_type' in df3.columns:
        df3 = df3[df3['profile_type'].isin(realistic_profiles)]

    if len(df3) > 0:
        subset_counts['low_current_discharge_dynamic']['rows'] += len(df3)
        if 'source_file' in df3.columns:
            subset_counts['low_current_discharge_dynamic']['files'].update(df3['source_file'].unique())
        if 'profile_type' in df3.columns:
            subset_counts['low_current_discharge_dynamic']['profiles'].update(df3['profile_type'].unique())
        if 'cell_id' in df3.columns:
            subset_counts['low_current_discharge_dynamic']['cells'].update(df3['cell_id'].unique())

        df3.to_parquet(
            subsets['low_current_discharge_dynamic'] / ("part_" + str(subset_counts['low_current_discharge_dynamic']['part_idx']) + ".parquet"),
            index=False, compression='snappy'
        )
        subset_counts['low_current_discharge_dynamic']['part_idx'] += 1

    del df, df1, df2, df3
    gc.collect()

    if (part_idx + 1) % 50 == 0:
        print("  Processed " + str(part_idx + 1) + "/" + str(len(lg_parts)))

print("\n" + "=" * 70)
print("SUBSET CREATION COMPLETE")
print("=" * 70 + "\n")

# ============================================================================
# GATHER STATISTICS
# ============================================================================
print("Gathering subset statistics...")

qa_rows = []
for subset_name, counts in subset_counts.items():
    if counts['rows'] == 0:
        continue

    # Read all parts to compute stats
    parts_to_read = sorted(glob.glob(str(subsets[subset_name] / "part_*.parquet")))

    voltage_vals = []
    temp_vals = []
    current_vals = []
    soc_vals = []

    for part in parts_to_read:
        df = pd.read_parquet(part)
        voltage_vals.extend(df['voltage_V'].values.tolist())
        temp_vals.extend(df['temperature_C'].values.tolist())
        current_vals.extend(df['current_abs_A'].values.tolist())
        soc_vals.extend(df['soc_target'].values.tolist())

    qa_rows.append({
        'subset': subset_name,
        'rows': counts['rows'],
        'files': len(counts['files']),
        'profiles': len(counts['profiles']),
        'cells': len(counts['cells']),
        'voltage_min': round(min(voltage_vals), 3) if voltage_vals else np.nan,
        'voltage_max': round(max(voltage_vals), 3) if voltage_vals else np.nan,
        'temp_min': round(min(temp_vals), 3) if temp_vals else np.nan,
        'temp_max': round(max(temp_vals), 3) if temp_vals else np.nan,
        'current_abs_min': round(min(current_vals), 3) if current_vals else np.nan,
        'current_abs_max': round(max(current_vals), 3) if current_vals else np.nan,
        'soc_min': round(min(soc_vals), 3) if soc_vals else np.nan,
        'soc_max': round(max(soc_vals), 3) if soc_vals else np.nan,
        'removed_rows': total_removed,
        'notes': str(list(counts['profiles']))[:50]
    })

# ============================================================================
# SAVE QA
# ============================================================================
print("Saving QA...\n")

pd.DataFrame(qa_rows).to_csv("outputs/external_datasets/lg18650_eval_subset_qa.csv", index=False)
print("Saved: outputs/external_datasets/lg18650_eval_subset_qa.csv")

# ============================================================================
# DECISION
# ============================================================================
clean_rows = next((r['rows'] for r in qa_rows if r['subset'] == 'clean_all_valid'), 0)
overlap_rows = next((r['rows'] for r in qa_rows if r['subset'] == 'oxford_overlap_strict'), 0)
dynamic_rows = next((r['rows'] for r in qa_rows if r['subset'] == 'low_current_discharge_dynamic'), 0)

min_threshold = 100000
if clean_rows < min_threshold:
    decision = "LG_EVAL_SUBSETS_TOO_SMALL"
    reason = "clean_all_valid < 100K rows"
elif overlap_rows < min_threshold * 0.1:
    decision = "LG_EVAL_SUBSETS_NEEDS_FIX"
    reason = "oxford_overlap_strict too small for reliable eval"
else:
    decision = "LG_EVAL_SUBSETS_READY"
    reason = "Sufficient rows for primary and stress eval"

# ============================================================================
# SAVE SUMMARY
# ============================================================================
print("Saving summary...\n")

with open("outputs/external_datasets/lg18650_eval_subset_summary.md", 'w') as f:
    f.write("# LG18650_HG2 Evaluation Subsets\n\n")
    f.write("## Subset Sizes\n\n")
    for row in qa_rows:
        f.write("- " + row['subset'] + ": " + str(row['rows']) + " rows, " + str(row['files']) + " files, " + str(row['cells']) + " cells\n")

    f.write("\n## Anomaly Removal\n\n")
    f.write("- Total input rows: " + str(total_input_rows) + "\n")
    f.write("- Rows removed: " + str(total_removed) + " (" + str(round(total_removed/total_input_rows*100, 1)) + "%)\n")
    f.write("- Filters: voltage [2.5-4.25]V, SOC [0-1], null checks, delta outliers\n\n")

    f.write("## Evaluation Strategy\n\n")
    f.write("- Primary eval: clean_all_valid (all valid profiles)\n")
    f.write("- Stress/OOD: low_current_discharge_dynamic (realistic discharge cycles)\n")
    if overlap_rows > 0:
        f.write("- Oxford validation: oxford_overlap_strict (" + str(overlap_rows) + " rows, " + str(round(overlap_rows/clean_rows*100, 1)) + "% of clean)\n")
    else:
        f.write("- Oxford validation: overlap subset is EMPTY - distributions incompatible\n")

    f.write("\n## Decision\n\n")
    f.write("**" + decision + "**\n\n")
    f.write("Reason: " + reason + "\n")

print("Saved: outputs/external_datasets/lg18650_eval_subset_summary.md\n")

print("=" * 70)
print("FINAL REPORT")
print("=" * 70)
print("clean_all_valid: " + str(clean_rows) + " rows")
print("oxford_overlap_strict: " + str(overlap_rows) + " rows")
print("low_current_discharge_dynamic: " + str(dynamic_rows) + " rows")
print("Removed: " + str(total_removed) + " rows")
print("Decision: " + decision)
print()
