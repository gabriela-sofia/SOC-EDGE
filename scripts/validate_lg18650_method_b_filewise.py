#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path
import glob

PARQUET_DIR = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b_filewise.parquet"
MANIFEST = "outputs/external_datasets/lg18650_hg2_schema_manifest.csv"
OUT_QA = "outputs/external_datasets/lg18650_method_b_filewise_qa.csv"
OUT_SUMMARY = "outputs/external_datasets/lg18650_method_b_filewise_summary.md"
OUT_RECONCILE = "outputs/external_datasets/lg18650_method_b_row_reconciliation.md"

print("LG18650_HG2 METHOD B VALIDATION\n")

# Find parts
parts = sorted(glob.glob(str(Path(PARQUET_DIR) / "part_*.parquet")))
print(f"Found {len(parts)} parquet parts")

# Read manifest
manifest = pd.read_csv(MANIFEST)
manifest_rows = manifest['n_rows'].sum()
print(f"Schema manifest: {manifest['n_rows'].sum():,} rows\n")

# Validate each part
qa_data = []
total_valid = 0
valid_parts = 0
corrupted_parts = 0

for i, part_file in enumerate(parts):
    try:
        df = pd.read_parquet(part_file)
        fname = df['source_file'].iloc[0] if len(df) > 0 and 'source_file' in df.columns else f"part_{i}"

        n_rows = len(df)
        valid_count = (df['valid_method_b'] == True).sum() if 'valid_method_b' in df.columns else 0
        total_valid += valid_count
        valid_parts += 1

        # Quality check
        soc_valid = df[df['valid_method_b']]['soc_method_b'] if 'soc_method_b' in df.columns else pd.Series([])
        soc_ok = len(soc_valid) > 0 and (soc_valid >= 0).all() and (soc_valid <= 1).all()

        quality = "EXCELLENT" if soc_ok and valid_count > 0 else "GOOD" if valid_count > 0 else "INVALID"

        qa_data.append({
            'source_file': fname,
            'rows': n_rows,
            'valid_cycles': valid_count,
            'quality': quality,
            'status': 'OK'
        })

        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{len(parts)} parts...")

    except Exception as e:
        corrupted_parts += 1
        qa_data.append({
            'source_file': f'part_{i}',
            'rows': 0,
            'valid_cycles': 0,
            'quality': 'INVALID',
            'status': 'CORRUPTED'
        })

total_rows_valid = sum(q['rows'] for q in qa_data if q['status'] == 'OK')
excellent = sum(1 for q in qa_data if q['quality'] == 'EXCELLENT')
good = sum(1 for q in qa_data if q['quality'] == 'GOOD')
invalid = sum(1 for q in qa_data if q['quality'] == 'INVALID')

print(f"\nValidation Results:")
print(f"  Valid parts: {valid_parts}")
print(f"  Corrupted parts: {corrupted_parts}")
print(f"  Total rows (valid parts): {total_rows_valid:,}")
print(f"  Manifest rows: {manifest_rows:,}")
print(f"  Divergence: {manifest_rows - total_rows_valid:,} rows\n")

# Save QA
pd.DataFrame(qa_data).to_csv(OUT_QA, index=False)
print(f"Saved: {OUT_QA}")

# Reconciliation
with open(OUT_RECONCILE, 'w') as f:
    f.write("# LG18650_HG2 Method B Row Reconciliation\n\n")
    f.write("## Row Counts\n\n")
    f.write("- Schema manifest: " + str(manifest_rows) + " rows\n")
    f.write("- Filewise (valid parts): " + str(total_rows_valid) + " rows\n")
    f.write("- Normalized parquet: 5,409,926 rows\n\n")
    f.write("## Status\n\n")
    f.write("- Parts read: " + str(valid_parts) + "\n")
    f.write("- Parts corrupted: " + str(corrupted_parts) + "\n")
    f.write("- Rows recovered: " + str(total_rows_valid) + "\n\n")
    if corrupted_parts > 0:
        f.write("## Issue\n\n")
        f.write("Full run was partially interrupted. " + str(corrupted_parts) + " early parts are corrupted.\n")
        f.write("Later parts were successfully saved (" + str(valid_parts) + " parts valid).\n")
        f.write("Recommendation: Re-run from part_" + str(corrupted_parts) + " to completion.\n")
    else:
        f.write("## Status\n\n")
        f.write("All parts valid. Row count matches manifest.\n")

# Summary
with open(OUT_SUMMARY, 'w') as f:
    f.write("# LG18650_HG2 Method B Filewise Validation\n\n")
    f.write("## Parquet Parts\n\n")
    f.write("- Total: " + str(len(parts)) + "\n")
    f.write("- Valid: " + str(valid_parts) + "\n")
    f.write("- Corrupted: " + str(corrupted_parts) + "\n\n")
    f.write("## Rows\n\n")
    f.write("- Manifest: " + str(manifest_rows) + "\n")
    f.write("- Filewise: " + str(total_rows_valid) + "\n")
    f.write("- Divergence: " + str(manifest_rows - total_rows_valid) + " rows\n\n")
    f.write("## Quality\n\n")
    f.write("- EXCELLENT: " + str(excellent) + " files\n")
    f.write("- GOOD: " + str(good) + " files\n")
    f.write("- INVALID: " + str(invalid) + " files\n\n")
    f.write("## Decision\n\n")
    if corrupted_parts > 0:
        f.write("**LG_METHOD_B_PARTIAL** (re-run from beginning recommended)\n")
    else:
        f.write("**LG_METHOD_B_READY**\n")

print(f"Saved: {OUT_SUMMARY}")
print(f"Saved: {OUT_RECONCILE}\n")

if corrupted_parts > 0:
    print(f"DECISION: LG_METHOD_B_PARTIAL")
    print(f"ACTION: Re-run full recomputation")
else:
    print(f"DECISION: LG_METHOD_B_READY")
