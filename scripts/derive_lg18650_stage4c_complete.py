#!/usr/bin/env python3
"""
Derive Stage 4C features from ALL valid Method B parts.
Process file-by-file, derive deltas and current_rel correctly.
No memory concatenation. Output reconciliation.
"""

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

print("=" * 70)
print("DERIVING STAGE 4C FEATURES FROM LG18650_HG2 METHOD B (COMPLETE RUN)")
print("=" * 70 + "\n")

# ============================================================================
# 1. LOAD QA AND BUILD QUALITY FILTER
# ============================================================================
qa_df = pd.read_csv(QA_INPUT)

# Calculate expected rows
expected_excellent = qa_df[qa_df['quality'] == 'EXCELLENT']['rows'].sum()
expected_good = qa_df[qa_df['quality'] == 'GOOD']['rows'].sum()
expected_rows = expected_excellent + expected_good

quality_ok_map = {}
for _, row in qa_df.iterrows():
    if row['quality'] in ['EXCELLENT', 'GOOD']:
        quality_ok_map[row['source_file']] = row['rows']

print("STEP 1: Quality Filter")
print("-" * 70)
print("Files EXCELLENT: " + str(len(qa_df[qa_df['quality'] == 'EXCELLENT'])))
print("Files GOOD: " + str(len(qa_df[qa_df['quality'] == 'GOOD'])))
print("Files INVALID: " + str(len(qa_df[qa_df['quality'] == 'INVALID'])))
print("Expected rows (EXCELLENT + GOOD): " + str(expected_rows) + "\n")

# ============================================================================
# 2. SETUP OUTPUT
# ============================================================================
output_path = Path(OUTPUT_PARQUET)
output_path.mkdir(parents=True, exist_ok=True)

parts_input = sorted(glob.glob(str(Path(PARQUET_DIR_INPUT) / "part_*.parquet")))
print("STEP 2: Input Parts")
print("-" * 70)
print("Total parts to process: " + str(len(parts_input)) + "\n")

# ============================================================================
# 3. PROCESS EACH PART
# ============================================================================
print("STEP 3: Processing Parts")
print("-" * 70)

qa_output = []
part_idx = 0
total_rows_processed = 0
total_rows_generated = 0
files_processed = 0
files_skipped = 0
invalid_skipped = 0

for i, part_file in enumerate(parts_input):
    # Try to read part
    try:
        df = pd.read_parquet(part_file)
    except:
        invalid_skipped += 1
        if (i + 1) % 50 == 0 or (i + 1) == len(parts_input):
            print("  [" + str(i + 1) + "/" + str(len(parts_input)) + "] Skipped corrupted")
        continue

    if len(df) == 0:
        invalid_skipped += 1
        continue

    # Get source file
    if 'source_file' not in df.columns:
        invalid_skipped += 1
        continue

    source_file = df['source_file'].iloc[0]

    # Filter by quality
    if source_file not in quality_ok_map:
        files_skipped += 1
        continue

    # Filter valid_method_b
    if 'valid_method_b' in df.columns:
        df = df[df['valid_method_b'] == True].copy()

    if len(df) == 0:
        files_skipped += 1
        continue

    files_processed += 1
    total_rows_processed += len(df)

    # ====================================================================
    # DERIVE STAGE 4C FEATURES
    # ====================================================================

    # Create output frame
    df_out = pd.DataFrame()

    # Copy core columns
    for col in ['dataset', 'cell_id', 'profile_type', 'temperature_condition',
                'cycle_id', 'source_file', 'time_s', 'voltage_V', 'temperature_C']:
        if col in df.columns:
            df_out[col] = df[col].values

    # current_abs_A
    df_out['current_abs_A'] = np.abs(df['current_A'].values)

    # Initialize deltas
    df_out['delta_voltage'] = 0.0
    df_out['delta_temperature'] = 0.0
    df_out['delta_current'] = 0.0
    df_out['current_rel'] = 0.0

    # Derive per source_file + cycle_id
    for (src_file, cyc_id), group_indices in df.groupby(['source_file', 'cycle_id'], sort=False).groups.items():
        # Get group and sort by time
        group = df.loc[group_indices].sort_values('time_s', ignore_index=False)
        indices = group.index.tolist()

        if len(indices) == 0:
            continue

        # Voltage: diff with first=0
        volt = df.loc[indices, 'voltage_V'].values
        df_out.loc[indices[0], 'delta_voltage'] = 0.0
        if len(indices) > 1:
            for j, idx in enumerate(indices[1:], 1):
                df_out.loc[idx, 'delta_voltage'] = volt[j] - volt[j - 1]

        # Temperature: diff with first=0
        temp = df.loc[indices, 'temperature_C'].values
        df_out.loc[indices[0], 'delta_temperature'] = 0.0
        if len(indices) > 1:
            for j, idx in enumerate(indices[1:], 1):
                df_out.loc[idx, 'delta_temperature'] = temp[j] - temp[j - 1]

        # Current: diff with first=0
        curr_abs = df_out.loc[indices, 'current_abs_A'].values
        df_out.loc[indices[0], 'delta_current'] = 0.0
        if len(indices) > 1:
            for j, idx in enumerate(indices[1:], 1):
                df_out.loc[idx, 'delta_current'] = curr_abs[j] - curr_abs[j - 1]

        # current_rel: per cycle max
        curr_max = np.max(np.abs(curr_abs))
        if curr_max > 1e-6:
            df_out.loc[indices, 'current_rel'] = curr_abs / curr_max
        else:
            df_out.loc[indices, 'current_rel'] = 0.0

    # SOC columns
    df_out['soc_target'] = df['soc_method_b'].values
    df_out['soc_source'] = 'method_b_lg_recomputed'

    # Eligible flag
    df_out['external_eval_eligible'] = (df['valid_method_b'] == True).values
    df_out['notes'] = 'current_rel_per_cycle_max'

    # Save part
    df_out.to_parquet(
        output_path / ("part_" + str(part_idx) + ".parquet"),
        index=False,
        compression='snappy'
    )

    total_rows_generated += len(df_out)
    part_idx += 1

    qa_output.append({
        'source_file': source_file,
        'rows_input': len(df),
        'rows_output': len(df_out),
        'eligible': (df_out['external_eval_eligible'] == True).sum()
    })

    # Progress
    if (i + 1) % 50 == 0 or (i + 1) == len(parts_input):
        pct = round((i + 1) / len(parts_input) * 100, 0)
        print("  [" + str(i + 1) + "/" + str(len(parts_input)) + "] " + str(pct) + "% - Files: " + str(files_processed) + ", Rows: " + str(total_rows_generated))

    del df, df_out
    gc.collect()

print("\n" + "=" * 70)
print("PROCESSING COMPLETE")
print("=" * 70 + "\n")

# ============================================================================
# 4. SAVE OUTPUTS
# ============================================================================
print("STEP 4: Saving Outputs")
print("-" * 70)

pd.DataFrame(qa_output).to_csv(OUT_QA, index=False)
print("Saved QA: " + OUT_QA)

# Summary
reconciliation_rate = (total_rows_generated / expected_rows * 100) if expected_rows > 0 else 0
decision = "LG_STAGE4C_FEATURES_READY" if total_rows_generated >= 0.98 * expected_rows else "LG_STAGE4C_FEATURES_NEEDS_FIX"

with open(OUT_SUMMARY, 'w') as f:
    f.write("# LG18650_HG2 Stage 4C Features\n\n")
    f.write("Expected rows: " + str(expected_rows) + "\n")
    f.write("Generated rows: " + str(total_rows_generated) + "\n")
    f.write("Reconciliation: " + str(round(reconciliation_rate, 1)) + "%\n\n")
    f.write("Files processed: " + str(files_processed) + "\n")
    f.write("Files skipped (low quality): " + str(files_skipped) + "\n")
    f.write("Parts invalid/corrupted: " + str(invalid_skipped) + "\n\n")
    f.write("Parquet parts: " + str(part_idx) + "\n")
    f.write("Schema: Stage 4C compatible\n\n")
    f.write("**Decision: " + decision + "**\n")

print("Saved summary: " + OUT_SUMMARY)

with open(OUT_RECONCILE, 'w') as f:
    f.write("# LG18650_HG2 Stage 4C Feature Reconciliation\n\n")
    f.write("## Expected vs Generated\n\n")
    f.write("- Expected rows (EXCELLENT+GOOD): " + str(expected_rows) + "\n")
    f.write("- Generated rows: " + str(total_rows_generated) + "\n")
    f.write("- Reconciliation rate: " + str(round(reconciliation_rate, 1)) + "%\n\n")
    f.write("## Files\n\n")
    f.write("- Processed: " + str(files_processed) + "\n")
    f.write("- Skipped (low quality): " + str(files_skipped) + "\n")
    f.write("- Invalid/corrupted: " + str(invalid_skipped) + "\n\n")
    f.write("## Status\n\n")
    if decision == "LG_STAGE4C_FEATURES_READY":
        f.write("All expected rows recovered. Decision: READY\n")
    else:
        f.write("Row count mismatch detected.\n")
        f.write("Investigation: Check if some parts failed in derivation.\n")

print("Saved reconciliation: " + OUT_RECONCILE + "\n")

# ============================================================================
# 5. FINAL REPORT
# ============================================================================
print("=" * 70)
print("FINAL REPORT")
print("=" * 70)
print("\nExpected rows: " + str(expected_rows))
print("Generated rows: " + str(total_rows_generated))
print("Files processed: " + str(files_processed))
print("Files skipped: " + str(files_skipped) + " (low quality)")
print("Parts invalid: " + str(invalid_skipped))
print("\nDecision: " + decision)

if decision != "LG_STAGE4C_FEATURES_READY":
    missing = expected_rows - total_rows_generated
    print("\nMissing rows: " + str(missing) + " (" + str(round((missing / expected_rows * 100), 1)) + "%)")
    if files_skipped > 0:
        print("Root cause: Some files in quality GOOD/EXCELLENT not in Method B parquet parts.")

print()
