#!/usr/bin/env python3
"""Fast Stage 4C derivation - process only quality-ok parts."""

import pandas as pd
import numpy as np
from pathlib import Path
import glob
import gc

PARQUET_DIR_INPUT = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b_filewise.parquet"
QA_INPUT = "outputs/external_datasets/lg18650_method_b_filewise_qa.csv"
OUTPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet"
OUT_QA = "outputs/external_datasets/lg18650_stage4c_feature_qa.csv"
OUT_SUMMARY = "outputs/external_datasets/lg18650_stage4c_feature_summary.md"
OUT_RECONCILE = "outputs/external_datasets/lg18650_stage4c_feature_reconciliation.md"

# Load QA
qa_df = pd.read_csv(QA_INPUT)
expected_rows = qa_df[qa_df['quality'].isin(['EXCELLENT', 'GOOD'])]['rows'].sum()
quality_ok_set = set(qa_df[qa_df['quality'].isin(['EXCELLENT', 'GOOD'])]['source_file'].tolist())

print("Expected rows: " + str(expected_rows))
print("Quality OK files: " + str(len(quality_ok_set)) + "\n")

# Find all parts and map source_file -> part
parts = sorted(glob.glob(str(Path(PARQUET_DIR_INPUT) / "part_*.parquet")))
source_to_part = {}
for part_idx, part_file in enumerate(parts):
    try:
        df_test = pd.read_parquet(part_file, columns=['source_file'])
        if len(df_test) > 0:
            source_file = df_test['source_file'].iloc[0]
            source_to_part[source_file] = part_idx
    except:
        pass

print("Parts found: " + str(len(parts)))
print("Unique source_files in parts: " + str(len(source_to_part)) + "\n")

# Build list of parts to process
parts_to_process = []
for source_file in quality_ok_set:
    if source_file in source_to_part:
        part_idx = source_to_part[source_file]
        parts_to_process.append((part_idx, parts[part_idx]))

print("Parts to process: " + str(len(parts_to_process)) + "\n")

# Setup output
output_path = Path(OUTPUT_PARQUET)
output_path.mkdir(parents=True, exist_ok=True)

# Process each part
qa_output = []
output_part_idx = 0
total_generated = 0
files_processed = 0

for original_part_idx, part_file in sorted(parts_to_process):
    try:
        df = pd.read_parquet(part_file)
    except:
        continue

    if len(df) == 0:
        continue

    source_file = df['source_file'].iloc[0] if 'source_file' in df.columns else None
    if not source_file or source_file not in quality_ok_set:
        continue

    # Filter valid
    if 'valid_method_b' in df.columns:
        df = df[df['valid_method_b'] == True].copy()

    if len(df) == 0:
        continue

    files_processed += 1

    # ================================================================
    # DERIVE STAGE 4C FEATURES
    # ================================================================
    df_out = pd.DataFrame()

    # Copy columns
    for col in ['dataset', 'cell_id', 'profile_type', 'temperature_condition',
                'cycle_id', 'source_file', 'time_s', 'voltage_V', 'temperature_C']:
        if col in df.columns:
            df_out[col] = df[col].values

    # Current
    df_out['current_abs_A'] = np.abs(df['current_A'].values)

    # Initialize deltas
    df_out['delta_voltage'] = 0.0
    df_out['delta_temperature'] = 0.0
    df_out['delta_current'] = 0.0
    df_out['current_rel'] = 0.0

    # Derive per cycle
    for (src_file, cyc_id), group_indices in df.groupby(['source_file', 'cycle_id'], sort=False).groups.items():
        group = df.loc[group_indices].sort_values('time_s', ignore_index=False)
        indices = group.index.tolist()

        if len(indices) == 0:
            continue

        # Voltage diff
        volt = df.loc[indices, 'voltage_V'].values
        df_out.loc[indices[0], 'delta_voltage'] = 0.0
        if len(indices) > 1:
            for j in range(1, len(indices)):
                df_out.loc[indices[j], 'delta_voltage'] = volt[j] - volt[j - 1]

        # Temperature diff
        temp = df.loc[indices, 'temperature_C'].values
        df_out.loc[indices[0], 'delta_temperature'] = 0.0
        if len(indices) > 1:
            for j in range(1, len(indices)):
                df_out.loc[indices[j], 'delta_temperature'] = temp[j] - temp[j - 1]

        # Current diff
        curr_abs = df_out.loc[indices, 'current_abs_A'].values
        df_out.loc[indices[0], 'delta_current'] = 0.0
        if len(indices) > 1:
            for j in range(1, len(indices)):
                df_out.loc[indices[j], 'delta_current'] = curr_abs[j] - curr_abs[j - 1]

        # current_rel
        curr_max = np.max(np.abs(curr_abs))
        if curr_max > 1e-6:
            df_out.loc[indices, 'current_rel'] = curr_abs / curr_max
        else:
            df_out.loc[indices, 'current_rel'] = 0.0

    # SOC
    df_out['soc_target'] = df['soc_method_b'].values
    df_out['soc_source'] = 'method_b_lg_recomputed'
    df_out['external_eval_eligible'] = (df['valid_method_b'] == True).values
    df_out['notes'] = 'current_rel_per_cycle_max'

    # Save
    df_out.to_parquet(
        output_path / ("part_" + str(output_part_idx) + ".parquet"),
        index=False,
        compression='snappy'
    )

    total_generated += len(df_out)
    output_part_idx += 1

    qa_output.append({
        'source_file': source_file,
        'rows_input': len(df),
        'rows_output': len(df_out),
        'eligible': (df_out['external_eval_eligible'] == True).sum()
    })

    if files_processed % 20 == 0:
        print("Processed: " + str(files_processed) + " files, " + str(total_generated) + " rows")

    del df, df_out
    gc.collect()

print("\n" + "=" * 70)

# Save
pd.DataFrame(qa_output).to_csv(OUT_QA, index=False)

reconciliation_rate = (total_generated / expected_rows * 100) if expected_rows > 0 else 0
decision = "LG_STAGE4C_FEATURES_READY" if total_generated >= 0.98 * expected_rows else "LG_STAGE4C_FEATURES_NEEDS_FIX"

with open(OUT_SUMMARY, 'w') as f:
    f.write("# LG18650_HG2 Stage 4C Features\n\n")
    f.write("Expected rows: " + str(expected_rows) + "\n")
    f.write("Generated rows: " + str(total_generated) + "\n")
    f.write("Reconciliation: " + str(round(reconciliation_rate, 1)) + "%\n\n")
    f.write("Files processed: " + str(files_processed) + "\n")
    f.write("Parquet parts: " + str(output_part_idx) + "\n\n")
    f.write("**Decision: " + decision + "**\n")

with open(OUT_RECONCILE, 'w') as f:
    f.write("# Reconciliation\n\n")
    f.write("Expected: " + str(expected_rows) + "\n")
    f.write("Generated: " + str(total_generated) + "\n")
    f.write("Match: " + str(round(reconciliation_rate, 1)) + "%\n")

print("Expected rows: " + str(expected_rows))
print("Generated rows: " + str(total_generated))
print("Files processed: " + str(files_processed))
print("Decision: " + decision)
print()
