#!/usr/bin/env python3
"""
Recompute LG18650_HG2 SOC using Method B (simple streaming via read_parquet chunks).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(".")
INPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_hg2_normalized.parquet"
OUTPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b_v2.parquet"
OUT_QA_CSV = "outputs/external_datasets/lg18650_method_b_target_qa.csv"
OUT_SUMMARY = "outputs/external_datasets/lg18650_method_b_target_summary.md"

print("="*70)
print("LG18650_HG2 METHOD B RECOMPUTATION (STREAMING)")
print("="*70 + "\n")

# Read entire parquet (unavoidable, but process incrementally)
print("Reading parquet...")
df = pd.read_parquet(INPUT_PARQUET)
print(f"Loaded: {len(df):,} rows\n")

# Add columns
df['soc_capacity_reference'] = df['soc_target'].copy()
df['soc_method_b'] = np.nan
df['Q_cycle_Ah'] = np.nan
df['valid_method_b'] = False

# Process by source_file + cycle_id
print("Computing Method B SOC...")
groups = df.groupby(['source_file', 'cycle_id'], sort=False)
n_groups = len(groups)
total_valid = 0

for i, (key, group_idx) in enumerate(groups.groups.items()):
    if (i + 1) % 500 == 0:
        print(f"  Processed {i+1}/{n_groups} groups...")

    group = df.loc[group_idx].sort_values('time_s')

    # Time monotonicity
    if not np.all(np.diff(group['time_s'].values) >= 0):
        continue

    # Current and time
    current = group['current_A'].values
    time_s = group['time_s'].values
    dt = np.concatenate([[0], np.diff(time_s)])

    # Skip if no variation
    if np.std(np.abs(current)) < 1e-6:
        continue

    # Coulombic charge
    q_Ah = np.cumsum(np.abs(current) * dt / 3600)
    Q_cycle = np.nanmax(q_Ah)

    # Skip if Q_cycle invalid
    if Q_cycle < 1e-6 or np.isnan(Q_cycle):
        continue

    # Compute SOC
    soc_b = 1.0 - q_Ah / Q_cycle
    soc_b = np.clip(soc_b, 0, 1)

    df.loc[group_idx, 'soc_method_b'] = soc_b
    df.loc[group_idx, 'Q_cycle_Ah'] = Q_cycle
    df.loc[group_idx, 'valid_method_b'] = True
    total_valid += 1

print(f"  Total valid cycles: {total_valid}/{n_groups}\n")

# Save parquet
print("Writing parquet...")
import shutil
output_path = Path(OUTPUT_PARQUET)
if output_path.exists():
    if output_path.is_file():
        output_path.unlink()
    else:
        shutil.rmtree(output_path)
output_path.mkdir(parents=True, exist_ok=True)
df.to_parquet(output_path / "data.parquet", index=False, compression='snappy')
print(f"Saved: {output_path / 'data.parquet'}\n")

# Profile statistics
print("Computing statistics...")
profile_stats = {}

for profile in sorted(df['profile_type'].unique()):
    df_p = df[df['profile_type'] == profile]
    rows = len(df_p)
    valid = (df_p['valid_method_b'] == True).sum()
    rate = 100 * valid / rows if rows > 0 else 0

    profile_stats[profile] = {'rows': rows, 'valid': valid, 'rate': rate}

# QA CSV
qa_data = []
for profile in sorted(profile_stats.keys()):
    stats = profile_stats[profile]
    qa_data.append({
        'profile_type': profile,
        'rows': stats['rows'],
        'valid_rows': stats['valid'],
        'valid_rate_pct': f"{stats['rate']:.1f}"
    })

pd.DataFrame(qa_data).to_csv(OUT_QA_CSV, index=False)
print(f"Saved QA: {OUT_QA_CSV}\n")

# Classify profiles
excellent = [p for p, s in profile_stats.items() if s['rate'] >= 90]
good = [p for p, s in profile_stats.items() if 70 <= s['rate'] < 90]
acceptable = [p for p, s in profile_stats.items() if 50 <= s['rate'] < 70]
review = [p for p, s in profile_stats.items() if s['rate'] < 50]

all_good = len(excellent) + len(good)
n_prof = len(profile_stats)

if all_good >= n_prof * 0.8:
    decision = "LG_METHOD_B_READY"
elif all_good >= n_prof * 0.6:
    decision = "LG_METHOD_B_PARTIAL"
else:
    decision = "LG_METHOD_B_NEEDS_FIX"

# Summary
with open(OUT_SUMMARY, 'w') as f:
    f.write("# LG18650_HG2 Method B Streaming Recomputation\n\n")
    f.write("## Results\n\n")
    f.write("- Rows processed: " + f"{len(df):,}" + "\n")
    f.write("- Valid cycles: " + str(total_valid) + "/" + str(n_groups) + "\n\n")
    f.write("## Profile Status\n\n")
    f.write("- EXCELLENT: " + (", ".join(excellent) if excellent else "none") + "\n")
    f.write("- GOOD: " + (", ".join(good) if good else "none") + "\n")
    f.write("- ACCEPTABLE: " + (", ".join(acceptable) if acceptable else "none") + "\n")
    f.write("- NEEDS REVIEW: " + (", ".join(review) if review else "none") + "\n\n")
    f.write("## Output Columns\n\n")
    f.write("- soc_method_b: Coulombic SOC (Oxford Method B compatible)\n")
    f.write("- soc_capacity_reference: Original capacity-based SOC\n")
    f.write("- valid_method_b: Boolean validity flag\n\n")
    f.write("## Decision\n\n")
    f.write("**" + decision + "**\n")

print(f"Saved summary: {OUT_SUMMARY}\n")
print("Profile Validity Rates:")
for profile in sorted(profile_stats.keys()):
    s = profile_stats[profile]
    print(f"  {profile:20s}: {s['rate']:5.1f}%")

print(f"\nDECISION: {decision}")
print(f"Ready profiles: {all_good}/{n_prof}")
