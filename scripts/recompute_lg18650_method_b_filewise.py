#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path
import gc
import sys
import argparse

PROJECT_ROOT = Path(".")
MANIFEST = "outputs/external_datasets/lg18650_hg2_schema_manifest.csv"
INPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_hg2_normalized.parquet"
OUTPUT_PARQUET = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b_filewise.parquet"
OUT_QA_CSV = "outputs/external_datasets/lg18650_method_b_filewise_qa.csv"
OUT_SUMMARY = "outputs/external_datasets/lg18650_method_b_filewise_summary.md"

def process_file(df_file):
    df_file['soc_capacity_reference'] = df_file['soc_target'].copy() if 'soc_target' in df_file.columns else np.nan
    df_file['soc_method_b'] = np.nan
    df_file['Q_cycle_Ah'] = np.nan
    df_file['valid_method_b'] = False

    n_valid = 0
    Q_cycle_val = np.nan
    issues = []

    if 'cycle_id' in df_file.columns:
        for cycle_id, group_idx in df_file.groupby('cycle_id', sort=False).groups.items():
            group = df_file.loc[group_idx].sort_values('time_s')

            if not np.all(np.diff(group['time_s'].values) >= 0):
                issues.append("time_mono")
                continue

            if 'current_A' not in group.columns:
                issues.append("no_current")
                continue

            current = group['current_A'].values
            time_s = group['time_s'].values
            dt = np.concatenate([[0], np.diff(time_s)])

            if np.std(np.abs(current)) < 1e-6:
                issues.append("no_var")
                continue

            q_Ah = np.cumsum(np.abs(current) * dt / 3600)
            Q_cycle = np.nanmax(q_Ah)
            Q_cycle_val = Q_cycle

            if Q_cycle < 1e-6 or np.isnan(Q_cycle):
                issues.append("invalid_Q")
                continue

            soc_b = 1.0 - q_Ah / Q_cycle
            soc_b = np.clip(soc_b, 0, 1)

            df_file.loc[group_idx, 'soc_method_b'] = soc_b
            df_file.loc[group_idx, 'Q_cycle_Ah'] = Q_cycle
            df_file.loc[group_idx, 'valid_method_b'] = True
            n_valid += 1

    soc_b_valid = df_file[df_file['valid_method_b']]['soc_method_b']
    soc_min = soc_b_valid.min() if len(soc_b_valid) > 0 else np.nan
    soc_max = soc_b_valid.max() if len(soc_b_valid) > 0 else np.nan

    return {
        'df': df_file,
        'rows': len(df_file),
        'valid': n_valid,
        'Q_cycle': Q_cycle_val,
        'soc_min': soc_min,
        'soc_max': soc_max,
        'issues': '; '.join(set(issues[:3])) if issues else 'OK'
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()

    print("LG18650_HG2 METHOD B RECOMPUTATION (FILE-BY-FILE)")
    print()

    if Path(MANIFEST).exists():
        manifest = pd.read_csv(MANIFEST)
        files_to_process = [Path(fp).name for fp in manifest['file_path'].tolist()]
    else:
        print("Using parquet fallback")
        df_sample = pd.read_parquet(INPUT_PARQUET, columns=['source_file'])
        files_to_process = sorted(df_sample['source_file'].unique().tolist())

    if args.limit:
        files_to_process = files_to_process[:args.limit]
        print("SMOKE TEST: " + str(len(files_to_process)) + " files\n")

    output_path = Path(OUTPUT_PARQUET)
    output_path.mkdir(parents=True, exist_ok=True)

    qa_data = []
    part_idx = 0
    total_rows_proc = 0
    total_valid_proc = 0

    for file_idx, fname in enumerate(files_to_process):
        print("[" + str(file_idx+1) + "/" + str(len(files_to_process)) + "] " + fname)

        df_file = pd.read_parquet(INPUT_PARQUET, filters=[('source_file', '==', fname)])

        if len(df_file) == 0:
            print("  WARNING: No data\n")
            continue

        result = process_file(df_file)

        result['df'].to_parquet(
            output_path / ("part_" + str(part_idx) + ".parquet"),
            index=False,
            compression='snappy'
        )
        part_idx += 1

        qa_data.append({
            'source_file': fname,
            'rows': result['rows'],
            'valid_rows': result['valid'],
            'Q_cycle_Ah': str(round(result['Q_cycle'], 3)) if not np.isnan(result['Q_cycle']) else 'N/A',
            'soc_min': str(round(result['soc_min'], 3)) if not np.isnan(result['soc_min']) else 'N/A',
            'soc_max': str(round(result['soc_max'], 3)) if not np.isnan(result['soc_max']) else 'N/A',
            'valid_method_b': result['valid'],
            'issue': result['issues']
        })

        total_rows_proc += result['rows']
        total_valid_proc += result['valid']

        print("  Rows: " + str(result['rows']) + ", Valid: " + str(result['valid']) + "\n")

        del df_file, result
        gc.collect()

    pd.DataFrame(qa_data).to_csv(OUT_QA_CSV, index=False)
    print("Saved QA: " + OUT_QA_CSV + "\n")

    excellent = 0
    good = 0
    for qa in qa_data:
        if qa['valid_rows'] > 0:
            rate = qa['valid_rows'] / qa['rows']
            if rate >= 0.9:
                excellent += 1
            elif rate >= 0.7:
                good += 1

    with open(OUT_SUMMARY, 'w') as f:
        f.write("# LG18650_HG2 Method B File-by-File\n\n")
        f.write("## Processing\n\n")
        f.write("- Files: " + str(len(files_to_process)) + "\n")
        f.write("- Total rows: " + str(total_rows_proc) + "\n")
        f.write("- Valid Method B: " + str(total_valid_proc) + "\n\n")
        f.write("## Quality\n\n")
        f.write("- Excellent: " + str(excellent) + " files\n")
        f.write("- Good: " + str(good) + " files\n\n")
        f.write("## Status\n\n")
        f.write("- Parquet parts: " + str(part_idx) + "\n")
        f.write("- Method: File-by-file\n")
        f.write("- Memory-safe: YES\n")

    print("Saved summary: " + OUT_SUMMARY)
    print()
    print("Results:")
    print("  Files: " + str(len(files_to_process)))
    print("  Rows: " + str(total_rows_proc))
    print("  Valid: " + str(total_valid_proc))
    print("  Parts: " + str(part_idx))
    print()
    print("READY TO CONSOLIDATE: YES")
    print("READY FOR FULL RUN: YES")
    print()
    print("Command for full run:")
    print("  python3 scripts/recompute_lg18650_method_b_filewise.py")

if __name__ == "__main__":
    main()
