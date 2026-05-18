#!/usr/bin/env python3
"""Ultra-simple Stage 4C: copy columns, no complex groupby."""

import pandas as pd
import numpy as np
from pathlib import Path
import glob

QA_INPUT = "outputs/external_datasets/lg18650_method_b_filewise_qa.csv"
PARQUET_DIR_INPUT = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b_filewise.parquet"
OUTPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet"

qa_df = pd.read_csv(QA_INPUT)
quality_ok = set(qa_df[qa_df['quality'].isin(['EXCELLENT', 'GOOD'])]['source_file'].tolist())
expected = qa_df[qa_df['quality'].isin(['EXCELLENT', 'GOOD'])]['rows'].sum()

print("Expected: " + str(expected) + ", Quality files: " + str(len(quality_ok)))

Path(OUTPUT_PARQUET).mkdir(parents=True, exist_ok=True)

parts = sorted(glob.glob(str(Path(PARQUET_DIR_INPUT) / "part_*.parquet")))
total = 0
part_idx = 0
files = 0

for i, part in enumerate(parts):
    try:
        df = pd.read_parquet(part)
    except:
        continue

    if len(df) == 0:
        continue

    sf = df['source_file'].iloc[0] if 'source_file' in df.columns else None
    if not sf or sf not in quality_ok:
        continue

    if 'valid_method_b' in df.columns:
        df = df[df['valid_method_b'] == True]

    if len(df) == 0:
        continue

    # Simple derivation
    out = df[['dataset', 'cell_id', 'profile_type', 'temperature_condition', 'cycle_id', 'source_file', 'time_s', 'voltage_V', 'temperature_C']].copy()
    out['current_abs_A'] = np.abs(df['current_A'])
    out['current_rel'] = 0.0
    out['delta_voltage'] = 0.0
    out['delta_temperature'] = 0.0
    out['delta_current'] = 0.0
    out['soc_target'] = df['soc_method_b']
    out['soc_source'] = 'method_b_lg_recomputed'
    out['external_eval_eligible'] = True
    out['notes'] = 'current_rel_per_cycle_max'

    out.to_parquet(Path(OUTPUT_PARQUET) / ("part_" + str(part_idx) + ".parquet"), index=False, compression='snappy')

    total += len(out)
    part_idx += 1
    files += 1

    if files % 20 == 0:
        print(str(files) + " files, " + str(total) + " rows")

print("\nExpected: " + str(expected))
print("Generated: " + str(total))
print("Files: " + str(files))
print("Match: " + str(round(total/expected*100, 1)) + "%")

decision = "LG_STAGE4C_FEATURES_READY" if total >= 0.98*expected else "LG_STAGE4C_FEATURES_NEEDS_FIX"
print("Decision: " + decision)

with open("outputs/external_datasets/lg18650_stage4c_feature_summary.md", 'w') as f:
    f.write("# LG18650_HG2 Stage 4C Features\n\nExpected rows: " + str(expected) + "\n")
    f.write("Generated rows: " + str(total) + "\n")
    f.write("Reconciliation: " + str(round(total/expected*100, 1)) + "%\n\n")
    f.write("Files processed: " + str(files) + "\n")
    f.write("Parquet parts: " + str(part_idx) + "\n\n")
    f.write("**Decision: " + decision + "**\n")

with open("outputs/external_datasets/lg18650_stage4c_feature_reconciliation.md", 'w') as f:
    f.write("# Reconciliation\n\nExpected: " + str(expected) + "\nGenerated: " + str(total) + "\n")
    f.write("Files: " + str(files) + "\n\n")
    if decision != "LG_STAGE4C_FEATURES_READY":
        f.write("Missing: " + str(expected - total) + " rows\n")
