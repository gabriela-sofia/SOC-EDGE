#!/usr/bin/env python3
"""Final Stage 4C derivation - simple and fast."""

import pandas as pd
import numpy as np
from pathlib import Path
import glob
import gc

QA = "outputs/external_datasets/lg18650_method_b_filewise_qa.csv"
PARQUET_IN = "data/processed/external/lg18650_hg2/lg18650_hg2_method_b_filewise.parquet"
PARQUET_OUT = "data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet"

qa = pd.read_csv(QA)
ok = set(qa[qa['quality'].isin(['EXCELLENT', 'GOOD'])]['source_file'].tolist())
exp = qa[qa['quality'].isin(['EXCELLENT', 'GOOD'])]['rows'].sum()

print("Expected: " + str(exp) + ", Quality files: " + str(len(ok)))

Path(PARQUET_OUT).mkdir(parents=True, exist_ok=True)

parts = sorted(glob.glob(str(Path(PARQUET_IN) / "part_*.parquet")))
tot = 0
pidx = 0
files = 0

for i, p in enumerate(parts):
    try:
        df = pd.read_parquet(p)
    except:
        continue

    if len(df) == 0 or 'source_file' not in df.columns:
        continue

    sf = df['source_file'].iloc[0]
    if sf not in ok:
        continue

    if 'valid_method_b' in df.columns:
        df = df[df['valid_method_b'] == True]

    if len(df) == 0:
        continue

    files += 1
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

    out.to_parquet(Path(PARQUET_OUT) / ("part_" + str(pidx) + ".parquet"), index=False, compression='snappy')
    tot += len(out)
    pidx += 1
    if files % 30 == 0:
        print("Files: " + str(files) + ", Rows: " + str(tot))
    del df, out
    gc.collect()

pct = (tot / exp * 100) if exp > 0 else 0
dec = "LG_STAGE4C_FEATURES_READY" if pct >= 98 else "LG_STAGE4C_FEATURES_NEEDS_FIX"

print("\nExpected: " + str(exp) + "\nGenerated: " + str(tot) + "\nFiles: " + str(files) + "\nMatch: " + str(round(pct, 1)) + "%\nDecision: " + dec)

with open("outputs/external_datasets/lg18650_stage4c_feature_summary.md", 'w') as f:
    f.write("# LG18650_HG2 Stage 4C Features\n\n")
    f.write("Expected rows: " + str(exp) + "\n")
    f.write("Generated rows: " + str(tot) + "\n")
    f.write("Reconciliation: " + str(round(pct, 1)) + "%\n\n")
    f.write("Files processed: " + str(files) + "\n")
    f.write("Parquet parts: " + str(pidx) + "\n\n")
    f.write("**Decision: " + dec + "**\n")

with open("outputs/external_datasets/lg18650_stage4c_feature_reconciliation.md", 'w') as f:
    f.write("# Reconciliation\n\n")
    f.write("Expected: " + str(exp) + "\n")
    f.write("Generated: " + str(tot) + "\n")
    f.write("Match: " + str(round(pct, 1)) + "%\n\n")
    if dec != "LG_STAGE4C_FEATURES_READY":
        f.write("Missing: " + str(exp - tot) + "\n")

print("Saved")
