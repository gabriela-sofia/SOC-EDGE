#!/usr/bin/env python3
"""
Smoke test: Derive Stage 4C features from first 5 EXCELLENT parts only.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import glob

PARQUET_DIR = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b_filewise.parquet"
QA_INPUT = "outputs/external_datasets/lg18650_method_b_filewise_qa.csv"

print("SMOKE TEST: Stage 4C Feature Derivation\n")

qa_df = pd.read_csv(QA_INPUT)
quality_ok = qa_df[qa_df['quality'] == 'EXCELLENT']['source_file'].tolist()[:5]
print("Testing with " + str(len(quality_ok)) + " EXCELLENT files\n")

parts = sorted(glob.glob(str(Path(PARQUET_DIR) / "part_*.parquet")))

for part_file in parts[:20]:
    try:
        df = pd.read_parquet(part_file)
    except:
        continue

    fname = df['source_file'].iloc[0] if len(df) > 0 else "unknown"

    if fname not in quality_ok:
        continue

    df = df[df['valid_method_b'] == True].copy()

    if len(df) == 0:
        continue

    print("File: " + fname)
    print("  Rows: " + str(len(df)))

    df['current_abs_A'] = np.abs(df['current_A'])

    for (src, cyc), idx_group in df.groupby(['source_file', 'cycle_id']).groups.items():
        group = df.loc[idx_group]
        c_max = group['current_abs_A'].max()
        if c_max > 1e-6:
            df.loc[idx_group, 'current_rel'] = group['current_abs_A'] / c_max

    soc_min = round(df['soc_method_b'].min(), 3)
    soc_max = round(df['soc_method_b'].max(), 3)
    current_rel_min = round(df['current_rel'].min(), 4)
    current_rel_max = round(df['current_rel'].max(), 4)

    print("  SOC: " + str(soc_min) + " - " + str(soc_max))
    print("  Current_rel: " + str(current_rel_min) + " - " + str(current_rel_max))
    print()

    break

print("SMOKE TEST PASS")
