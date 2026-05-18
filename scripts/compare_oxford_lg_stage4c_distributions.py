#!/usr/bin/env python3
"""
Compare Oxford vs LG Stage 4C distributions.
QA on voltage, temperature, current, deltas, SOC.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import glob
import gc

print("=" * 70)
print("OXFORD vs LG STAGE 4C DISTRIBUTION QA")
print("=" * 70 + "\n")

# ============================================================================
# LOAD OXFORD
# ============================================================================
print("Loading Oxford Stage 4C...")

oxford_csvs = sorted(glob.glob("CORE/stage4c_final_results/processed/cell_Cell*_processed.csv"))
print("Found " + str(len(oxford_csvs)) + " Oxford cells\n")

oxford_dfs = []
for csv_file in oxford_csvs:
    try:
        df = pd.read_csv(csv_file)
        oxford_dfs.append(df)
    except:
        pass

oxford = pd.concat(oxford_dfs, ignore_index=True)
print("Oxford total rows: " + str(len(oxford)))
print("Oxford cells: " + str(oxford['cell_name'].nunique()))

# ============================================================================
# LOAD LG
# ============================================================================
print("\nLoading LG Stage 4C...")

lg_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet/part_*.parquet"))
print("Found " + str(len(lg_parts)) + " LG parts\n")

lg_dfs = []
for part in lg_parts:
    try:
        df = pd.read_parquet(part)
        lg_dfs.append(df)
    except:
        pass

lg = pd.concat(lg_dfs, ignore_index=True)
print("LG total rows: " + str(len(lg)))
print("LG cells: " + str(lg['cell_id'].nunique() if 'cell_id' in lg.columns else "N/A"))

# ============================================================================
# COMPARE DISTRIBUTIONS
# ============================================================================
print("\n" + "=" * 70)
print("DISTRIBUTION COMPARISON")
print("=" * 70 + "\n")

features = ['voltage_V', 'temperature_C', 'current_abs_A', 'current_rel',
            'delta_voltage', 'delta_temperature', 'delta_current', 'soc_target']

qa_rows = []

for feat in features:
    print("Feature: " + feat)

    # Oxford
    if feat in oxford.columns:
        ox_vals = oxford[feat].dropna()
        ox_min = ox_vals.min()
        ox_max = ox_vals.max()
        ox_mean = ox_vals.mean()
        ox_p01 = ox_vals.quantile(0.01)
        ox_p99 = ox_vals.quantile(0.99)
        ox_missing = (oxford[feat].isnull().sum() / len(oxford) * 100)
    else:
        ox_min = ox_max = ox_mean = ox_p01 = ox_p99 = ox_missing = np.nan

    # LG
    if feat in lg.columns:
        lg_vals = lg[feat].dropna()
        lg_min = lg_vals.min()
        lg_max = lg_vals.max()
        lg_mean = lg_vals.mean()
        lg_p01 = lg_vals.quantile(0.01)
        lg_p99 = lg_vals.quantile(0.99)
        lg_missing = (lg[feat].isnull().sum() / len(lg) * 100)
    else:
        lg_min = lg_max = lg_mean = lg_p01 = lg_p99 = lg_missing = np.nan

    # Report
    print("  Oxford: [" + str(round(ox_min, 3)) + ", " + str(round(ox_max, 3)) + "], mean=" + str(round(ox_mean, 3)))
    print("  LG:     [" + str(round(lg_min, 3)) + ", " + str(round(lg_max, 3)) + "], mean=" + str(round(lg_mean, 3)))
    print()

    qa_rows.append({
        'feature': feat,
        'oxford_min': ox_min,
        'oxford_max': ox_max,
        'oxford_mean': ox_mean,
        'oxford_p01': ox_p01,
        'oxford_p99': ox_p99,
        'lg_min': lg_min,
        'lg_max': lg_max,
        'lg_mean': lg_mean,
        'lg_p01': lg_p01,
        'lg_p99': lg_p99,
        'oxford_missing': ox_missing,
        'lg_missing': lg_missing
    })

# ============================================================================
# DETECT SHIFTS
# ============================================================================
print("Detecting distribution shifts...")

shifts = []
for row in qa_rows:
    feat = row['feature']

    # Check range shift
    ox_range = row['oxford_max'] - row['oxford_min']
    lg_range = row['lg_max'] - row['lg_min']

    # Check mean shift
    ox_mean = row['oxford_mean']
    lg_mean = row['lg_mean']

    if ox_range > 0:
        range_ratio = lg_range / ox_range
        if range_ratio < 0.5 or range_ratio > 2.0:
            shifts.append(feat + ": range ratio=" + str(round(range_ratio, 2)))

    if not np.isnan(ox_mean) and not np.isnan(lg_mean):
        mean_diff_pct = abs(lg_mean - ox_mean) / abs(ox_mean) * 100 if ox_mean != 0 else 0
        if mean_diff_pct > 10:
            shifts.append(feat + ": mean shift=" + str(round(mean_diff_pct, 1)) + "%")

print("Shifts detected: " + str(len(shifts)))
for s in shifts[:5]:
    print("  - " + s)

# ============================================================================
# SAVE QA
# ============================================================================
print("\nSaving QA...")

qa_df = pd.DataFrame(qa_rows)
qa_df.to_csv("outputs/external_datasets/oxford_lg_stage4c_distribution_qa.csv", index=False)

print("Saved: outputs/external_datasets/oxford_lg_stage4c_distribution_qa.csv")

# ============================================================================
# DECISION
# ============================================================================
print("\nMaking decision...")

# Check if distributions are compatible
major_shifts = len(shifts)
temp_shift = any('temperature_C' in s for s in shifts)
current_shift = any('current' in s for s in shifts)
soc_shift = any('soc' in s for s in shifts)

if major_shifts == 0:
    decision = "READY_FOR_EXTERNAL_MODEL_EVAL"
    reason = "Distributions compatible with Oxford"
elif temp_shift or current_shift:
    decision = "NEEDS_RANGE_FILTER"
    reason = "Temperature or current ranges need filtering"
elif soc_shift or major_shifts > 2:
    decision = "NEEDS_FEATURE_FIX"
    reason = "SOC or multiple features show incompatibility"
else:
    decision = "READY_FOR_EXTERNAL_MODEL_EVAL"
    reason = "Minor shifts, acceptable"

print("Decision: " + decision)
print("Reason: " + reason)

# ============================================================================
# SAVE SUMMARY
# ============================================================================
print("\nSaving summary...")

with open("outputs/external_datasets/oxford_lg_stage4c_distribution_summary.md", 'w') as f:
    f.write("# Oxford vs LG Stage 4C Distribution QA\n\n")
    f.write("## Dataset Overview\n\n")
    f.write("- Oxford rows: " + str(len(oxford)) + ", cells: " + str(oxford['cell_name'].nunique()) + "\n")
    f.write("- LG rows: " + str(len(lg)) + ", cells: " + str(lg['cell_id'].nunique() if 'cell_id' in lg.columns else "N/A") + "\n\n")

    f.write("## Distribution Shifts Detected\n\n")
    f.write("- Total shifts: " + str(major_shifts) + "\n")
    if shifts:
        for s in shifts[:5]:
            f.write("  - " + s + "\n")
    else:
        f.write("  - No major shifts\n")

    f.write("\n## Risk Assessment\n\n")
    if temp_shift:
        f.write("- Temperature range mismatch: may require filtering by temperature condition\n")
    if current_shift:
        f.write("- Current profile mismatch: check if profile types are compatible\n")
    if soc_shift:
        f.write("- SOC range incompatibility: may indicate Method B divergence\n")

    f.write("\n## Recommendation\n\n")
    f.write("- Filter LG by: temperature_condition if temp_shift, profile_type if current_shift\n")
    f.write("- Monitor: deltas (voltage, temperature, current) during model evaluation\n\n")

    f.write("## Decision\n\n")
    f.write("**" + decision + "**\n\n")
    f.write("Reason: " + reason + "\n")

print("Saved: outputs/external_datasets/oxford_lg_stage4c_distribution_summary.md\n")

print("=" * 70)
print("SUMMARY")
print("=" * 70)
print("Oxford: " + str(len(oxford)) + " rows, " + str(oxford['cell_name'].nunique()) + " cells")
print("LG: " + str(len(lg)) + " rows, " + str(lg['cell_id'].nunique() if 'cell_id' in lg.columns else "N/A") + " cells")
print("Shifts: " + str(major_shifts))
print("Decision: " + decision)
print()
