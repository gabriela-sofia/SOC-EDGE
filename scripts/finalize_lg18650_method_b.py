#!/usr/bin/env python3
"""
Finalize Method B results: read parquet, compute stats, generate reports.
"""

import pandas as pd
import numpy as np
from pathlib import Path

pq_path = Path("data/processed/external/lg18650_hg2/lg18650_hg2_method_b_v2.parquet")
out_qa = "outputs/external_datasets/lg18650_method_b_target_qa.csv"
out_sum = "outputs/external_datasets/lg18650_method_b_target_summary.md"

print("Reading parquet...")
df = pd.read_parquet(str(pq_path / "data.parquet"))
print(f"Loaded: {len(df):,} rows\n")

# Stats
total_valid = (df['valid_method_b'] == True).sum()
n_groups = df.groupby(['source_file', 'cycle_id']).ngroups

print(f"Valid cycles: {total_valid}/{n_groups}\n")

# By profile
profiles = df['profile_type'].unique()
qa_list = []

for prof in sorted(profiles):
    df_p = df[df['profile_type'] == prof]
    rows = len(df_p)
    valid = (df_p['valid_method_b'] == True).sum()
    rate = 100 * valid / rows if rows > 0 else 0
    qa_list.append({'profile_type': prof, 'rows': rows, 'valid_rows': valid, 'valid_rate_pct': f"{rate:.1f}"})

# Save QA
pd.DataFrame(qa_list).to_csv(out_qa, index=False)
print(f"Saved: {out_qa}\n")

# Classification
excellent = [p for p in profiles if 100*len(df[(df['profile_type']==p) & (df['valid_method_b']==True)])/len(df[df['profile_type']==p]) >= 90]
good = [p for p in profiles if 70 <= 100*len(df[(df['profile_type']==p) & (df['valid_method_b']==True)])/len(df[df['profile_type']==p]) < 90]

if len(excellent) + len(good) >= len(profiles) * 0.8:
    decision = "LG_METHOD_B_READY"
elif len(excellent) + len(good) >= len(profiles) * 0.6:
    decision = "LG_METHOD_B_PARTIAL"
else:
    decision = "LG_METHOD_B_NEEDS_FIX"

# Summary
with open(out_sum, 'w') as f:
    f.write("# LG18650_HG2 Method B Recomputation\n\n")
    f.write("## Results\n\n")
    f.write(f"- Rows processed: {len(df):,}\n")
    f.write(f"- Valid cycles: {total_valid}/{n_groups}\n\n")
    f.write("## Profile Status\n\n")
    f.write("- EXCELLENT: " + (", ".join(excellent) if excellent else "none") + "\n")
    f.write("- GOOD: " + (", ".join(good) if good else "none") + "\n\n")
    f.write("## Output\n\n")
    f.write("- soc_method_b: Coulombic SOC (Oxford-compatible)\n")
    f.write("- soc_capacity_reference: Original capacity-based\n")
    f.write("- valid_method_b: Boolean validity flag\n\n")
    f.write("## Decision\n\n")
    f.write(f"**{decision}**\n")

print(f"Saved: {out_sum}\n")
print(f"DECISION: {decision}")
