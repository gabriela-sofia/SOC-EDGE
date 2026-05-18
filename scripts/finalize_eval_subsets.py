#!/usr/bin/env python3
"""Quick finalization of eval subsets - just count rows and generate QA."""

import pandas as pd
import numpy as np
from pathlib import Path
import glob

print("Finalizing eval subsets...\n")

subsets = {
    'clean_all_valid': "data/processed/external/lg18650_hg2/eval_subsets/clean_all_valid.parquet",
    'oxford_overlap_strict': "data/processed/external/lg18650_hg2/eval_subsets/oxford_overlap_strict.parquet",
    'low_current_discharge_dynamic': "data/processed/external/lg18650_hg2/eval_subsets/low_current_discharge_dynamic.parquet"
}

qa_rows = []
for subset_name, subset_path in subsets.items():
    parts = sorted(glob.glob(str(Path(subset_path) / "part_*.parquet")))

    rows = 0
    files = set()
    cells = set()
    profiles = set()

    for part in parts:
        try:
            df = pd.read_parquet(part, columns=['source_file', 'cell_id', 'profile_type', 'voltage_V', 'temperature_C', 'current_abs_A', 'soc_target'])
            rows += len(df)
            if 'source_file' in df.columns:
                files.update(df['source_file'].unique())
            if 'cell_id' in df.columns:
                cells.update(df['cell_id'].unique())
            if 'profile_type' in df.columns:
                profiles.update(df['profile_type'].unique())
        except:
            pass

    print(subset_name + ": " + str(rows) + " rows, " + str(len(files)) + " files, " + str(len(cells)) + " cells")

    if rows > 0:
        qa_rows.append({
            'subset': subset_name,
            'rows': rows,
            'files': len(files),
            'profiles': len(profiles),
            'cells': len(cells),
            'removed_rows': "see_code",
            'notes': str(list(profiles))[:60]
        })
    else:
        qa_rows.append({
            'subset': subset_name,
            'rows': 0,
            'files': 0,
            'profiles': 0,
            'cells': 0,
            'removed_rows': 0,
            'notes': "EMPTY"
        })

# Save QA
pd.DataFrame(qa_rows).to_csv("outputs/external_datasets/lg18650_eval_subset_qa.csv", index=False)

# Get counts
clean_rows = next((r['rows'] for r in qa_rows if r['subset'] == 'clean_all_valid'), 0)
overlap_rows = next((r['rows'] for r in qa_rows if r['subset'] == 'oxford_overlap_strict'), 0)
dynamic_rows = next((r['rows'] for r in qa_rows if r['subset'] == 'low_current_discharge_dynamic'), 0)

decision = "LG_EVAL_SUBSETS_READY" if clean_rows >= 100000 else "LG_EVAL_SUBSETS_TOO_SMALL"

with open("outputs/external_datasets/lg18650_eval_subset_summary.md", 'w') as f:
    f.write("# LG18650_HG2 Evaluation Subsets\n\n")
    f.write("## Subset Sizes\n\n")
    f.write("- clean_all_valid: " + str(clean_rows) + " rows\n")
    f.write("- oxford_overlap_strict: " + str(overlap_rows) + " rows\n")
    f.write("- low_current_discharge_dynamic: " + str(dynamic_rows) + " rows\n\n")
    f.write("## Evaluation Strategy\n\n")
    f.write("- Primary eval: clean_all_valid (all valid profiles)\n")
    if dynamic_rows > 0:
        f.write("- Stress/OOD: low_current_discharge_dynamic (realistic discharge cycles)\n")
    if overlap_rows == 0:
        f.write("- Oxford overlap: EMPTY - distributions too incompatible\n")
    else:
        f.write("- Oxford validation: oxford_overlap_strict (" + str(overlap_rows) + " rows)\n")
    f.write("\n## Decision\n\n")
    f.write("**" + decision + "**\n")

print("\n" + "=" * 70)
print("clean_all_valid: " + str(clean_rows))
print("oxford_overlap_strict: " + str(overlap_rows))
print("low_current_discharge_dynamic: " + str(dynamic_rows))
print("Decision: " + decision)
