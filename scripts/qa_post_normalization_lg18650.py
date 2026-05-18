#!/usr/bin/env python3
"""
QA post-normalization for LG18650_HG2 parquet.
Check ranges, issues, train_eligible distribution.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import csv

PROJECT_ROOT = Path(".")
PARQUET_PATH = Path("data/processed/external/lg18650_hg2/lg18650_hg2_normalized.parquet")
OUT_QA_CSV = Path("outputs/external_datasets/lg18650_hg2_post_normalization_qa.csv")
OUT_SUMMARY = Path("outputs/external_datasets/lg18650_hg2_post_normalization_summary.md")

print("Reading parquet...")
try:
    df = pd.read_parquet(PARQUET_PATH)
except Exception as e:
    print(f"ERROR reading parquet: {e}")
    exit(1)

print(f"Total rows: {len(df):,}")
print(f"Columns: {list(df.columns)}\n")

# Detect issues globally
issues = []

# SOC range
soc_out_of_range = ((df['soc_target'] < -0.01) | (df['soc_target'] > 1.01)).sum()
if soc_out_of_range > 0:
    issues.append(f"SOC out of range [0,1]: {soc_out_of_range} rows")

# Voltage range (3.0 - 4.2V is typical for Li-ion)
volt_out = ((df['voltage_V'] < 2.5) | (df['voltage_V'] > 4.3)).sum()
if volt_out > 0:
    issues.append(f"Voltage out of [2.5, 4.3]V: {volt_out} rows")

# Current: check for excessive zeros
curr_zero = (df['current_A'] == 0).sum()
curr_zero_pct = 100 * curr_zero / len(df)
if curr_zero_pct > 50:
    issues.append(f"Current zero rate: {curr_zero_pct:.1f}%")

# Temperature: check for nulls
temp_null = df['temperature_C'].isna().sum()
if temp_null > 0:
    issues.append(f"Temperature null: {temp_null} rows")

# Capacity: check for nulls
cap_null = df['capacity_Ah'].isna().sum()
if cap_null > 0:
    issues.append(f"Capacity null: {cap_null} rows")

# SOC inversions: check if SOC mostly inverted (mean > 0.7 for discharge)
for profile in df['profile_type'].unique():
    df_prof = df[df['profile_type'] == profile]
    if 'discharge' in profile.lower():
        soc_mean = df_prof['soc_target'].mean()
        if soc_mean > 0.7:
            issues.append(f"Profile {profile}: high SOC mean ({soc_mean:.2f}) - may be inverted")

print(f"Global issues detected: {len(issues)}")
for issue in issues:
    print(f"  - {issue}")

# QA by profile_type and train_eligible
qa_rows = []

for profile in sorted(df['profile_type'].unique()):
    for train_eligible in [False, True]:
        subset = df[(df['profile_type'] == profile) & (df['train_eligible'] == train_eligible)]

        if len(subset) == 0:
            continue

        n_rows = len(subset)
        n_files = subset['source_file'].nunique()
        n_cells = subset['cell_id'].nunique()

        soc = subset['soc_target']
        volt = subset['voltage_V']
        curr = subset['current_A']
        temp = subset['temperature_C']
        cap = subset['capacity_Ah']

        # Check monotonicity of time (within files)
        time_mono_files = 0
        for fname in subset['source_file'].unique():
            df_file = subset[subset['source_file'] == fname].sort_values('time_s')
            if (df_file['time_s'].diff().dropna() >= 0).all():
                time_mono_files += 1

        missing_rate = (subset[['voltage_V', 'current_A', 'temperature_C', 'capacity_Ah', 'soc_target']].isna().sum().sum()) / (len(subset) * 5)

        qa_rows.append({
            'profile_type': profile,
            'train_eligible': train_eligible,
            'rows': n_rows,
            'files': n_files,
            'cell_count': n_cells,
            'soc_min': f"{soc.min():.4f}",
            'soc_max': f"{soc.max():.4f}",
            'soc_mean': f"{soc.mean():.4f}",
            'voltage_min': f"{volt.min():.2f}",
            'voltage_max': f"{volt.max():.2f}",
            'current_min': f"{curr.min():.3f}",
            'current_max': f"{curr.max():.3f}",
            'temp_min': f"{temp.min():.1f}",
            'temp_max': f"{temp.max():.1f}",
            'capacity_min': f"{cap.min():.3f}",
            'capacity_max': f"{cap.max():.3f}",
            'missing_rate': f"{missing_rate:.3f}",
            'time_monotonic_rate': f"{time_mono_files / n_files:.2f}",
            'issues': 'none' if len(issues) == 0 else 'see_global'
        })

# Save QA CSV
with open(OUT_QA_CSV, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=qa_rows[0].keys())
    writer.writeheader()
    writer.writerows(qa_rows)

print(f"\n✓ QA CSV saved: {OUT_QA_CSV}")
print(f"  {len(qa_rows)} groups analyzed")

# Determine readiness
readiness = "READY_FOR_OXFORD_ALIGNMENT"
if len(issues) > 0:
    readiness = "NEEDS_FIX"

# Summary
with open(OUT_SUMMARY, 'w') as f:
    f.write("# LG18650_HG2 Post-Normalization QA Summary\n\n")

    f.write(f"## Coverage\n")
    f.write(f"- **Total rows:** {len(df):,}\n")
    f.write(f"- **Files:** {df['source_file'].nunique()}\n")
    f.write(f"- **Cells:** {df['cell_id'].nunique()}\n")
    f.write(f"- **Profiles:** {df['profile_type'].nunique()}\n")
    f.write(f"- **Train-eligible:** {(df['train_eligible'] == True).sum():,} rows\n\n")

    f.write("## Ranges\n\n")
    f.write(f"- SOC: [{df['soc_target'].min():.4f}, {df['soc_target'].max():.4f}]\n")
    f.write(f"- Voltage: [{df['voltage_V'].min():.2f}, {df['voltage_V'].max():.2f}]V\n")
    f.write(f"- Current: [{df['current_A'].min():.3f}, {df['current_A'].max():.3f}]A\n")
    f.write(f"- Temperature: [{df['temperature_C'].min():.1f}, {df['temperature_C'].max():.1f}]°C\n")
    f.write(f"- Capacity: [{df['capacity_Ah'].min():.3f}, {df['capacity_Ah'].max():.3f}]Ah\n\n")

    f.write("## Issues\n\n")
    if len(issues) == 0:
        f.write("- None detected\n\n")
    else:
        for issue in issues[:5]:  # Top 5
            f.write(f"- {issue}\n")
        f.write("\n")

    f.write("## Decision\n\n")
    f.write(f"**{readiness}**\n\n")

    f.write("## Next\n\n")
    if readiness == "READY_FOR_OXFORD_ALIGNMENT":
        f.write("```bash\npython3 scripts/validate_cross_dataset_oxford.py\n```\n")
    else:
        f.write("```bash\nReview lg18650_hg2_post_normalization_qa.csv for issues\n```\n")

print(f"✓ Summary saved: {OUT_SUMMARY}")
print(f"\nDECISION: {readiness}")

if len(issues) > 0:
    print(f"\nIssues found ({len(issues)}):")
    for issue in issues[:10]:
        print(f"  - {issue}")

print("\n" + "="*60)
print(f"POST-NORMALIZATION QA: {readiness}")
print("="*60)
