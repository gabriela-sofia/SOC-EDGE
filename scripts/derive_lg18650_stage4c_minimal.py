#!/usr/bin/env python3
"""Minimal Stage 4C derivation - just copy and derive basic columns."""

import pandas as pd
import numpy as np
from pathlib import Path
import glob
import gc

QA_INPUT = "outputs/external_datasets/lg18650_method_b_filewise_qa.csv"
PARQUET_DIR_INPUT = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b_filewise.parquet"
OUTPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet"

# Load quality map
qa_df = pd.read_csv(QA_INPUT)
quality_ok = set(qa_df[qa_df['quality'].isin(['EXCELLENT', 'GOOD'])]['source_file'].tolist())
expected_rows = qa_df[qa_df['quality'].isin(['EXCELLENT', 'GOOD'])]['rows'].sum()

print("Expected: " + str(expected_rows) + ", Quality OK files: " + str(len(quality_ok)))

# Find all parts
parts = sorted(glob.glob(str(Path(PARQUET_DIR_INPUT) / "part_*.parquet")))
print("Total parts: " + str(len(parts)))

# Setup output
Path(OUTPUT_PARQUET).mkdir(parents=True, exist_ok=True)

# Process
total_generated = 0
part_idx = 0
files_processed = 0

for i, part_file in enumerate(parts):
    try:
        df = pd.read_parquet(part_file)
    except:
        continue

    if len(df) == 0:
        continue

    source_file = df['source_file'].iloc[0] if 'source_file' in df.columns else None
    if not source_file or source_file not in quality_ok:
        continue

    # Filter valid
    if 'valid_method_b' in df.columns:
        df = df[df['valid_method_b'] == True]

    if len(df) == 0:
        continue

    files_processed += 1

    # Derive Stage 4C columns
    df_out = df[[
        'dataset', 'cell_id', 'profile_type', 'temperature_condition',
        'cycle_id', 'source_file', 'time_s', 'voltage_V', 'temperature_C'
    ]].copy()

    df_out['current_abs_A'] = np.abs(df['current_A'])
    df_out['soc_target'] = df['soc_method_b']
    df_out['soc_source'] = 'method_b_lg_recomputed'
    df_out['external_eval_eligible'] = True
    df_out['notes'] = 'current_rel_per_cycle_max'

    # Deltas and current_rel - simple version
    df_out['current_rel'] = 0.0
    df_out['delta_voltage'] = 0.0
    df_out['delta_temperature'] = 0.0
    df_out['delta_current'] = 0.0

    for (src, cyc), idx_list in df.groupby(['source_file', 'cycle_id']).groups.items():
        idx_sorted = df.loc[idx_list].sort_values('time_s').index.tolist()

        if len(idx_sorted) > 0:
            # current_rel
            c_abs = df_out.loc[idx_sorted, 'current_abs_A'].values
            c_max = np.max(np.abs(c_abs))
            if c_max > 1e-6:
                df_out.loc[idx_sorted, 'current_rel'] = c_abs / c_max

            # Deltas
            df_out.loc[idx_sorted[0], 'delta_voltage'] = 0.0
            df_out.loc[idx_sorted[0], 'delta_temperature'] = 0.0
            df_out.loc[idx_sorted[0], 'delta_current'] = 0.0

            if len(idx_sorted) > 1:
                v = df_out.loc[idx_sorted, 'voltage_V'].values
                t = df_out.loc[idx_sorted, 'temperature_C'].values
                c = df_out.loc[idx_sorted, 'current_abs_A'].values

                for j in range(1, len(idx_sorted)):
                    df_out.loc[idx_sorted[j], 'delta_voltage'] = v[j] - v[j-1]
                    df_out.loc[idx_sorted[j], 'delta_temperature'] = t[j] - t[j-1]
                    df_out.loc[idx_sorted[j], 'delta_current'] = c[j] - c[j-1]

    # Save
    df_out.to_parquet(
        Path(OUTPUT_PARQUET) / ("part_" + str(part_idx) + ".parquet"),
        index=False, compression='snappy'
    )

    total_generated += len(df_out)
    part_idx += 1

    if files_processed % 10 == 0:
        print("Files: " + str(files_processed) + ", Rows: " + str(total_generated))

    del df, df_out
    gc.collect()

print("\n" + "=" * 70)
print("Expected: " + str(expected_rows))
print("Generated: " + str(total_generated))
print("Files: " + str(files_processed))
match_pct = (total_generated / expected_rows * 100) if expected_rows > 0 else 0
print("Match: " + str(round(match_pct, 1)) + "%")

decision = "LG_STAGE4C_FEATURES_READY" if match_pct >= 98 else "LG_STAGE4C_FEATURES_NEEDS_FIX"
print("Decision: " + decision)

# Save summary
with open("outputs/external_datasets/lg18650_stage4c_feature_summary.md", 'w') as f:
    f.write("# LG18650_HG2 Stage 4C Features\n\n")
    f.write("Expected rows: " + str(expected_rows) + "\n")
    f.write("Generated rows: " + str(total_generated) + "\n")
    f.write("Reconciliation: " + str(round(match_pct, 1)) + "%\n\n")
    f.write("Files processed: " + str(files_processed) + "\n")
    f.write("Parquet parts: " + str(part_idx) + "\n\n")
    f.write("**Decision: " + decision + "**\n")

with open("outputs/external_datasets/lg18650_stage4c_feature_reconciliation.md", 'w') as f:
    f.write("# Reconciliation\n\n")
    f.write("Expected: " + str(expected_rows) + "\n")
    f.write("Generated: " + str(total_generated) + "\n")
    f.write("Files processed: " + str(files_processed) + "\n")
    f.write("Match: " + str(round(match_pct, 1)) + "%\n\n")
    if decision != "LG_STAGE4C_FEATURES_READY":
        missing = expected_rows - total_generated
        f.write("Missing rows: " + str(missing) + "\n")
        f.write("Cause: Verification needed - check if all valid files processed\n")

print("\nOutputs saved")
