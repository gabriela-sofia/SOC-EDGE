"""
V8B3 -- Generate synthetic ESP32 log for validator dry-run.

Uses canonical reference CSVs to create a perfect synthetic log
(SOC values exactly matching clipped reference) then runs the validator.
Outputs dry-run metrics JSON and report.
"""

import os
import sys
import csv
import json
import subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(BASE, 'handoff_esp32_v8b2_canonical')
OUTDIR = os.path.join(BASE, 'outputs', 'v8b3_handoff_freeze')
REPLAY = os.path.join(HANDOFF, 'replay')
ANOMALY_DIR = os.path.join(HANDOFF, 'anomaly')
VAL_SCRIPT = os.path.join(HANDOFF, 'validation', 'validate_esp32_v8b2.py')

os.makedirs(OUTDIR, exist_ok=True)

LATENCY_SIM = 0.191      # matching V8A baseline
HEAP_SIM = 299604
MIN_HEAP_SIM = 299604
MAX_ALLOC_SIM = 300000

# ---------------------------------------------------------------------------
# Build synthetic log
# ---------------------------------------------------------------------------

lines = []
lines.append('// V8B3 dry-run synthetic log -- perfect ESP32 simulation')
lines.append('// Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
lines.append('// schema: sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status')
lines.append('// BEGIN_GOLDEN')

# GOLDEN: 20 samples from golden reference
golden_path = os.path.join(REPLAY, 'canonical_golden_vectors_v8b2.csv')
with open(golden_path, encoding='utf-8') as f:
    golden_rows = list(csv.DictReader(f))

for i, row in enumerate(golden_rows):
    soc = float(row['soc_clipped_reference'])
    is_sat = int(row.get('is_saturated', '0'))
    status = 'WARN_SAT' if is_sat else 'PASS'
    lines.append(f'{i},GOLDEN,{soc:.6f},{LATENCY_SIM:.3f},{HEAP_SIM},{MIN_HEAP_SIM},{MAX_ALLOC_SIM},0,0,{status}')

lines.append('// END_GOLDEN')
lines.append('// BEGIN_EXTENDED')

# EXTENDED: 120 samples from extended reference
ext_ref_path = os.path.join(REPLAY, 'canonical_extended_reference_v8b2.csv')
with open(ext_ref_path, encoding='utf-8') as f:
    ext_rows = list(csv.DictReader(f))

for i, row in enumerate(ext_rows):
    soc = float(row['soc_clipped_reference'])
    is_sat = int(row.get('is_saturated', '0'))
    status = 'WARN_SAT' if is_sat else 'PASS'
    lines.append(f'{i},EXTENDED,{soc:.6f},{LATENCY_SIM:.3f},{HEAP_SIM},{MIN_HEAP_SIM},{MAX_ALLOC_SIM},0,0,{status}')

lines.append('// END_EXTENDED')
lines.append('// BEGIN_ANOMALY')

# ANOMALY: 10 scenarios -- simulate correct detection for embedded-feasible ones
flags_path = os.path.join(ANOMALY_DIR, 'anomaly_expected_flags_v8b2.csv')
with open(flags_path, encoding='utf-8') as f:
    flag_rows = list(csv.DictReader(f))

for i, row in enumerate(flag_rows):
    exp_flag = int(row['expected_anomaly_flag'])
    exp_code = int(row.get('expected_anomaly_code', '0'))
    embedded = row.get('embedded_feasible', 'YES').strip().upper()
    # Simulate: embedded feasible = detected; reference_only = not detected
    obs_flag = exp_flag if embedded == 'YES' else 0
    obs_code = exp_code if obs_flag else 0
    status = 'ANOMALY' if obs_flag else 'PASS'
    lines.append(f'{i},ANOMALY,0.500000,{LATENCY_SIM:.3f},{HEAP_SIM},{MIN_HEAP_SIM},{MAX_ALLOC_SIM},{obs_flag},{obs_code},{status}')

lines.append('// END_ANOMALY')
lines.append('// DONE')

log_path = os.path.join(OUTDIR, 'v8b3_dry_run_synthetic_log.txt')
with open(log_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')

print(f'Synthetic log written: {log_path}')
print(f'  GOLDEN: {len(golden_rows)} samples')
print(f'  EXTENDED: {len(ext_rows)} samples')
print(f'  ANOMALY: {len(flag_rows)} scenarios')

# ---------------------------------------------------------------------------
# Run validator
# ---------------------------------------------------------------------------

val_out_dir = os.path.join(OUTDIR, 'dry_run_output')
os.makedirs(val_out_dir, exist_ok=True)

print(f'\nRunning validator...')
result = subprocess.run(
    [sys.executable, VAL_SCRIPT, log_path, '--output-dir', val_out_dir],
    capture_output=True, text=True, encoding='utf-8'
)
print('STDOUT:', result.stdout[:3000] if result.stdout else '(none)')
if result.returncode != 0:
    print('STDERR:', result.stderr[:2000])

# ---------------------------------------------------------------------------
# Copy/summarize outputs
# ---------------------------------------------------------------------------

import shutil

metrics_src = os.path.join(val_out_dir, 'v8b2_validation_metrics.json')
report_src = os.path.join(val_out_dir, 'v8b2_validation_report.md')

metrics_dst = os.path.join(OUTDIR, 'v8b3_validator_dry_run_metrics.json')
report_dst = os.path.join(OUTDIR, 'v8b3_validator_dry_run_report.md')

if os.path.exists(metrics_src):
    shutil.copy2(metrics_src, metrics_dst)
    print(f'Metrics: {metrics_dst}')
    with open(metrics_dst, encoding='utf-8') as f:
        m = json.load(f)
    print(json.dumps(m, indent=2)[:2000])
else:
    print('ERROR: metrics JSON not generated')
    blockers = [{'blocker': 'validator did not generate metrics JSON', 'stderr': result.stderr[:500]}]
    blk_path = os.path.join(OUTDIR, 'v8b3_validator_dry_run_blockers.csv')
    with open(blk_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['blocker','stderr'])
        w.writeheader()
        w.writerows(blockers)
    print(f'Blockers written: {blk_path}')

if os.path.exists(report_src):
    shutil.copy2(report_src, report_dst)
    print(f'Report: {report_dst}')
else:
    print('ERROR: validation report not generated')
