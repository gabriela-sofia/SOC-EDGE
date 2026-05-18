#!/usr/bin/env python3
"""
Recompute LG18650_HG2 SOC using Method B (coulombic integration per cycle).
ULTRA-OPTIMIZED: process in-place without full reload, minimal memory.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow.parquet as pq

PROJECT_ROOT = Path(".")
INPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_hg2_normalized.parquet"
OUTPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b.parquet"
OUT_QA_CSV = "outputs/external_datasets/lg18650_method_b_target_qa.csv"
OUT_SUMMARY = "outputs/external_datasets/lg18650_method_b_target_summary.md"

print("="*70)
print("LG18650_HG2 METHOD B SOC RECOMPUTATION")
print("="*70 + "\n")

# Load parquet (partitioned directory)
df = pd.read_parquet(INPUT_PARQUET)
print(f"Loaded: {len(df)} rows from partitioned parquet\n")

# Preserve original
df['soc_capacity_reference'] = df['soc_target']
df['soc_method_b'] = np.nan
df['Q_cycle_Ah'] = np.nan
df['valid_method_b'] = False

# Process by file-cycle
groups = df.groupby(['source_file', 'cycle_id'], sort=False)
total_groups = len(groups)
valid_count = 0

print(f"Processing {total_groups} file-cycle groups...")

for i, (key, group_idx) in enumerate(groups.groups.items()):
    if i % 500 == 0:
        print(f"  {i}/{total_groups}")

    group = df.loc[group_idx].sort_values('time_s')

    # Time monotonicity
    time_ok = np.all(np.diff(group['time_s'].values) >= 0)

    if not time_ok:
        continue

    # Coulombic charge
    current = group['current_A'].values
    time_s = group['time_s'].values
    dt = np.concatenate([[0], np.diff(time_s)])
    q_Ah = np.cumsum(np.abs(current) * dt / 3600)
    Q_cycle = np.nanmax(q_Ah)

    # Check validity
    current_var = np.std(np.abs(current)) > 1e-6
    Q_ok = Q_cycle > 1e-6

    if not (current_var and Q_ok):
        continue

    # Compute SOC
    soc_b = 1.0 - q_Ah / Q_cycle
    soc_b = np.clip(soc_b, 0, 1)

    df.loc[group_idx, 'soc_method_b'] = soc_b
    df.loc[group_idx, 'Q_cycle_Ah'] = Q_cycle
    df.loc[group_idx, 'valid_method_b'] = True
    valid_count += 1

print(f"\nValid Method B: {valid_count}/{total_groups} groups\n")

# Save parquet
Path(OUTPUT_PARQUET).parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(OUTPUT_PARQUET, index=False, compression='snappy')
print(f"Saved parquet: {OUTPUT_PARQUET}\n")

# QA by profile
qa_data = []
profile_verdicts = {}

for profile in sorted(df['profile_type'].unique()):
    df_p = df[df['profile_type'] == profile]

    n_rows = len(df_p)
    n_files = df_p['source_file'].nunique()
    valid_rows = (df_p['valid_method_b'] == True).sum()
    valid_rate = 100 * valid_rows / n_rows if n_rows > 0 else 0

    # Ranges
    soc_b = df_p[df_p['valid_method_b']]['soc_method_b']
    Q_c = df_p[df_p['valid_method_b']]['Q_cycle_Ah']

    soc_min = soc_b.min() if len(soc_b) > 0 else np.nan
    soc_max = soc_b.max() if len(soc_b) > 0 else np.nan
    Q_min = Q_c.min() if len(Q_c) > 0 else np.nan
    Q_max = Q_c.max() if len(Q_c) > 0 else np.nan

    # Comparison
    mask = df_p['valid_method_b'] & df_p['soc_capacity_reference'].notna() & df_p['soc_method_b'].notna()
    if mask.sum() > 10:
        mae = np.mean(np.abs(df_p.loc[mask, 'soc_method_b'].values - df_p.loc[mask, 'soc_capacity_reference'].values))
        corr = np.corrcoef(df_p.loc[mask, 'soc_method_b'].values, df_p.loc[mask, 'soc_capacity_reference'].values)[0, 1]
    else:
        mae = np.nan
        corr = np.nan

    qa_data.append({
        'profile_type': profile,
        'rows': n_rows,
        'files': n_files,
        'valid_rows': valid_rows,
        'valid_rate_pct': f"{valid_rate:.1f}",
        'Q_min_Ah': f"{Q_min:.3f}" if not np.isnan(Q_min) else "N/A",
        'Q_max_Ah': f"{Q_max:.3f}" if not np.isnan(Q_max) else "N/A",
        'soc_min': f"{soc_min:.3f}" if not np.isnan(soc_min) else "N/A",
        'soc_max': f"{soc_max:.3f}" if not np.isnan(soc_max) else "N/A",
        'mae_vs_cap': f"{mae:.4f}" if not np.isnan(mae) else "N/A",
        'corr_vs_cap': f"{corr:.3f}" if not np.isnan(corr) else "N/A",
        'issue': 'OK' if valid_rate >= 70 else 'CHECK'
    })

    if valid_rate >= 90:
        profile_verdicts[profile] = 'EXCELLENT'
    elif valid_rate >= 70:
        profile_verdicts[profile] = 'GOOD'
    elif valid_rate >= 50:
        profile_verdicts[profile] = 'ACCEPTABLE'
    else:
        profile_verdicts[profile] = 'NEEDS_REVIEW'

pd.DataFrame(qa_data).to_csv(OUT_QA_CSV, index=False)
print(f"Saved QA CSV: {OUT_QA_CSV}\n")

# Decision
excellent = [p for p, v in profile_verdicts.items() if v == 'EXCELLENT']
good = [p for p, v in profile_verdicts.items() if v == 'GOOD']
acceptable = [p for p, v in profile_verdicts.items() if v == 'ACCEPTABLE']
review = [p for p, v in profile_verdicts.items() if v == 'NEEDS_REVIEW']

all_good = len(excellent) + len(good)
n_profiles = len(profile_verdicts)

if all_good >= n_profiles * 0.8:
    decision = "LG_METHOD_B_READY"
elif all_good + len(acceptable) >= n_profiles * 0.7:
    decision = "LG_METHOD_B_PARTIAL"
else:
    decision = "LG_METHOD_B_NEEDS_FIX"

# Summary
with open(OUT_SUMMARY, 'w') as f:
    f.write("# LG18650_HG2 Method B SOC Recomputation\n\n")
    f.write("## Method\n\n")
    f.write("Per file-cycle: Q_cycle = max(integral(abs(I) dt)), SOC = 1 - Q/Q_cycle\n\n")
    f.write("## Results\n\n")
    f.write("- Valid file-cycles: " + str(valid_count) + "/" + str(total_groups) + "\n\n")

    f.write("## Profile Status\n\n")
    f.write("- EXCELLENT: " + (', '.join(excellent) if excellent else 'none') + "\n")
    f.write("- GOOD: " + (', '.join(good) if good else 'none') + "\n")
    f.write("- ACCEPTABLE: " + (', '.join(acceptable) if acceptable else 'none') + "\n")
    f.write("- NEEDS_REVIEW: " + (', '.join(review) if review else 'none') + "\n\n")
    f.write("## Decision\n\n")
    f.write("**" + decision + "**\n")

print("Saved summary: " + OUT_SUMMARY)
print("\nProfile Verdicts:")
for profile in sorted(profile_verdicts.keys()):
    print("  " + profile + ": " + profile_verdicts[profile])

print("\nDECISION: " + decision)
print("Ready profiles: " + str(all_good) + "/" + str(n_profiles))
