"""
V8B3 -- Freeze Audit Script

Tasks:
  T1: Package inventory CSV
  T2: SHA256 checksums CSV
  T3: Consistency audit CSV
  T5: Freeze lock manifest JSON

Run from SOC_PROJECT root.
"""

import os
import sys
import csv
import json
import hashlib
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(BASE, 'handoff_esp32_v8b2_canonical')
OUTDIR = os.path.join(BASE, 'outputs', 'v8b3_handoff_freeze')
REPORTS = os.path.join(BASE, 'REPORTS')

os.makedirs(OUTDIR, exist_ok=True)

# ---------------------------------------------------------------------------
# T1: Package inventory
# ---------------------------------------------------------------------------

REQUIRED_FILES = [
    ('README.md',                                          'doc',       True,  'Package overview'),
    ('LEIA_PRIMEIRO_ESP32.md',                             'doc',       True,  'Execution guide (PT)'),
    ('MENSAGEM_PARA_PESSOA_DA_ESP_V8B2.md',                'doc',       True,  'Short message for executor'),
    ('firmware/firmware_soc_v8b2_canonical.ino',           'firmware',  True,  'Main firmware (3 modes)'),
    ('firmware/canonical_model_weights_v8b2.h',            'firmware',  True,  'MLP weights C header'),
    ('firmware/replay_vectors_v8b2.h',                     'firmware',  True,  'Replay vectors C header'),
    ('model/MODEL_MANIFEST_V8B2.md',                       'model',     True,  'Model specification'),
    ('model/canonical_feature_order_v7c.json',             'model',     True,  'Feature order'),
    ('model/canonical_scaler_params_v7c.json',             'model',     True,  'Scaler bounds'),
    ('model/canonical_golden_vectors_v7c.csv',             'model',     True,  'Golden vectors (orig)'),
    ('model/canonical_expected_serial_output_v7c.csv',     'model',     True,  'Expected serial (orig)'),
    ('model/canonical_model_weights_v7c.json',             'model',     True,  'Model weights JSON'),
    ('replay/canonical_golden_vectors_v8b2.csv',           'replay',    True,  'Golden replay (20)'),
    ('replay/canonical_extended_replay_v8b2.csv',          'replay',    True,  'Extended replay (120)'),
    ('replay/canonical_extended_reference_v8b2.csv',       'replay',    True,  'Extended reference (120)'),
    ('replay/canonical_saturation_cases_v8b2.csv',         'replay',    True,  'Saturation cases (6)'),
    ('replay/canonical_replay_manifest_v8b2.csv',          'replay',    True,  'Replay manifest'),
    ('anomaly/anomaly_replay_scenarios_v8b2.csv',          'anomaly',   True,  'Anomaly scenarios (10)'),
    ('anomaly/anomaly_expected_flags_v8b2.csv',            'anomaly',   True,  'Expected flags (10)'),
    ('anomaly/anomaly_manifest_v8b2.csv',                  'anomaly',   True,  'Anomaly manifest'),
    ('validation/validate_esp32_v8b2.py',                  'validator', True,  'Python validator'),
    ('results_template/RESULT_TEMPLATE_ESP32_V8B2_CANONICAL.md', 'doc', True,  'Return template'),
]

print('=== T1: Package Inventory ===')
inventory = []
for rel, ftype, required, notes in REQUIRED_FILES:
    full = os.path.join(HANDOFF, rel)
    exists = os.path.exists(full)
    size = os.path.getsize(full) if exists else 0
    status = 'OK' if exists else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL')
    inventory.append({
        'path': rel,
        'exists': str(exists),
        'file_type': ftype,
        'required': str(required),
        'size_bytes': size,
        'status': status,
        'notes': notes,
    })
    marker = 'OK' if exists else 'MISS'
    print(f'  [{marker}] {rel} ({size} bytes)')

inv_path = os.path.join(OUTDIR, 'v8b3_package_inventory.csv')
with open(inv_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['path','exists','file_type','required','size_bytes','status','notes'])
    w.writeheader()
    w.writerows(inventory)

missing = [r for r in inventory if r['status'].startswith('MISSING_REQUIRED')]
print(f'\nInventory: {len(inventory)} files, {len(missing)} MISSING_REQUIRED')
print(f'Saved: {inv_path}')

# ---------------------------------------------------------------------------
# T2: Checksums
# ---------------------------------------------------------------------------

print('\n=== T2: SHA256 Checksums ===')

FILE_ROLES = {
    'firmware/firmware_soc_v8b2_canonical.ino': 'firmware_main',
    'firmware/canonical_model_weights_v8b2.h': 'model_weights_header',
    'firmware/replay_vectors_v8b2.h': 'replay_vectors_header',
    'model/canonical_scaler_params_v7c.json': 'scaler_params',
    'model/canonical_model_weights_v7c.json': 'model_weights',
    'model/canonical_golden_vectors_v7c.csv': 'golden_vectors_orig',
    'replay/canonical_golden_vectors_v8b2.csv': 'golden_replay',
    'replay/canonical_extended_replay_v8b2.csv': 'extended_replay',
    'replay/canonical_extended_reference_v8b2.csv': 'extended_reference',
    'replay/canonical_saturation_cases_v8b2.csv': 'saturation_cases',
    'anomaly/anomaly_replay_scenarios_v8b2.csv': 'anomaly_scenarios',
    'anomaly/anomaly_expected_flags_v8b2.csv': 'anomaly_expected_flags',
    'validation/validate_esp32_v8b2.py': 'python_validator',
}

checksums = []
for rel, role in FILE_ROLES.items():
    full = os.path.join(HANDOFF, rel)
    if not os.path.exists(full):
        checksums.append({'path': rel, 'sha256': 'FILE_MISSING', 'size_bytes': 0, 'role': role, 'status': 'MISSING'})
        continue
    h = hashlib.sha256()
    with open(full, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    sha = h.hexdigest()
    size = os.path.getsize(full)
    checksums.append({'path': rel, 'sha256': sha, 'size_bytes': size, 'role': role, 'status': 'OK'})
    print(f'  {rel[:50]:<50} {sha[:16]}... {size}B')

ck_path = os.path.join(OUTDIR, 'v8b3_package_checksums.csv')
with open(ck_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['path','sha256','size_bytes','role','status'])
    w.writeheader()
    w.writerows(checksums)
print(f'Saved: {ck_path}')

# ---------------------------------------------------------------------------
# T3: Consistency audit
# ---------------------------------------------------------------------------

print('\n=== T3: Consistency Audit ===')

import pandas as pd

def audit_check(name, result, expected, notes=''):
    status = 'OK' if result == expected else 'FAIL'
    marker = 'OK' if status == 'OK' else 'FAIL'
    print(f'  [{marker}] {name}: got={result!r} expected={expected!r}')
    return {'check': name, 'result': str(result), 'expected': str(expected), 'status': status, 'notes': notes}

def audit_contains(name, filepath, substring, notes=''):
    if not os.path.exists(filepath):
        print(f'  ✗ {name}: FILE MISSING')
        return {'check': name, 'result': 'FILE_MISSING', 'expected': f'contains:{substring[:30]}', 'status': 'FAIL', 'notes': notes}
    content = open(filepath, encoding='utf-8').read()
    found = substring in content
    status = 'OK' if found else 'FAIL'
    marker = 'OK' if found else 'FAIL'
    print(f'  [{marker}] {name}: {"found" if found else "NOT FOUND"} in {os.path.basename(filepath)}')
    return {'check': name, 'result': str(found), 'expected': 'True', 'status': status, 'notes': notes}

audit_rows = []

# Sample counts
gv_df = pd.read_csv(os.path.join(HANDOFF, 'replay/canonical_golden_vectors_v8b2.csv'))
ext_df = pd.read_csv(os.path.join(HANDOFF, 'replay/canonical_extended_replay_v8b2.csv'))
sat_df = pd.read_csv(os.path.join(HANDOFF, 'replay/canonical_saturation_cases_v8b2.csv'))
ref_df = pd.read_csv(os.path.join(HANDOFF, 'replay/canonical_extended_reference_v8b2.csv'))
anom_df = pd.read_csv(os.path.join(HANDOFF, 'anomaly/anomaly_replay_scenarios_v8b2.csv'))
flags_df = pd.read_csv(os.path.join(HANDOFF, 'anomaly/anomaly_expected_flags_v8b2.csv'))

audit_rows.append(audit_check('golden_sample_count', len(gv_df), 20))
audit_rows.append(audit_check('extended_sample_count', len(ext_df), 120))
audit_rows.append(audit_check('extended_reference_count', len(ref_df), 120))
audit_rows.append(audit_check('saturation_case_count', len(sat_df), 6, 'documented saturated samples'))
audit_rows.append(audit_check('anomaly_scenario_count', len(anom_df), 10))
audit_rows.append(audit_check('anomaly_flags_count', len(flags_df), 10))

# is_saturated column in reference
n_sat_ref = int(ref_df['is_saturated'].astype(int).sum()) if 'is_saturated' in ref_df.columns else -1
audit_rows.append(audit_check('saturated_in_reference', n_sat_ref, 6))

# soc_clipped_reference column exists
audit_rows.append(audit_check('clipped_reference_col_in_extended', 'soc_clipped_reference' in ref_df.columns, True))
audit_rows.append(audit_check('clipped_reference_col_in_golden', 'soc_clipped_reference' in gv_df.columns, True))

# Schema 10 fields
SCHEMA = 'sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status'
readme_path = os.path.join(HANDOFF, 'README.md')
val_path = os.path.join(HANDOFF, 'validation/validate_esp32_v8b2.py')
audit_rows.append(audit_contains('schema_10_fields_in_readme', readme_path, SCHEMA))
audit_rows.append(audit_contains('schema_10_fields_in_validator', val_path, 'sample_id'))

# MAE threshold
audit_rows.append(audit_contains('mae_threshold_in_validator', val_path, 'MAE_THRESHOLD = 0.001'))
audit_rows.append(audit_contains('mae_threshold_in_readme', readme_path, '0.001'))

# Anomaly recall threshold
audit_rows.append(audit_contains('recall_threshold_in_validator', val_path, 'ANOMALY_RECALL_THRESHOLD = 0.90'))
audit_rows.append(audit_contains('recall_threshold_in_readme', readme_path, '0.90'))

# Clipping documented
fw_path = os.path.join(HANDOFF, 'firmware/firmware_soc_v8b2_canonical.ino')
audit_rows.append(audit_contains('clipping_in_firmware', fw_path, 'fmaxf'))
audit_rows.append(audit_contains('clipping_in_manifest', os.path.join(HANDOFF, 'model/MODEL_MANIFEST_V8B2.md'), 'clip'))

# soc_clipped_reference as acceptance criterion
audit_rows.append(audit_contains('clipped_ref_as_criterion_in_readme', readme_path, 'clipped'))

# GOLDEN validator merge -- known issue: uses sample_id string vs int
val_src = open(val_path, encoding='utf-8').read()
golden_merge_positional = 'ref_idx' in val_src and 'validate_golden' in val_src
# Check if golden merge uses positional (ref_idx) -- it currently uses sample_id merge
golden_uses_sample_id_merge = 'left_on=\'sample_id\'' in val_src or 'left_on="sample_id"' in val_src
validator_golden_merge_issue = golden_uses_sample_id_merge
marker = 'FAIL' if validator_golden_merge_issue else 'OK'
print(f'  [{marker}] golden_validator_merge: uses sample_id string merge (ESP32 outputs int) -> VALIDATOR_BUG_DETECTED')
audit_rows.append({
    'check': 'golden_validator_merge_compatible',
    'result': str(not validator_golden_merge_issue),
    'expected': 'True',
    'status': 'FAIL' if validator_golden_merge_issue else 'OK',
    'notes': 'Firmware outputs int sample_id; golden reference has string gv_XX; merge will fail to match -- fix needed',
})

ca_path = os.path.join(OUTDIR, 'v8b3_consistency_audit.csv')
with open(ca_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['check','result','expected','status','notes'])
    w.writeheader()
    w.writerows(audit_rows)

n_fail = sum(1 for r in audit_rows if r['status'] == 'FAIL')
print(f'\nConsistency: {len(audit_rows)} checks, {n_fail} FAIL')
print(f'Saved: {ca_path}')

# ---------------------------------------------------------------------------
# T5: Freeze lock manifest
# ---------------------------------------------------------------------------

print('\n=== T5: Freeze Lock Manifest ===')

# Determine ready_to_zip: only block on truly critical issues (missing required files)
n_missing = len(missing)
blockers = []
if n_missing > 0:
    blockers.append(f'{n_missing} required file(s) missing from package')
if validator_golden_merge_issue:
    blockers.append('Validator GOLDEN merge uses sample_id string vs int -- fix before hardware run')

ready_to_zip = len([b for b in blockers if 'missing' in b.lower()]) == 0

lock = {
    'package_name': 'handoff_esp32_v8b2_canonical',
    'package_version': 'V8B3',
    'created_from_phase': 'V8B2_CANONICAL_EXTENDED_REPLAY_ANOMALY_AND_STRESS_HANDOFF_PACKAGE',
    'date_frozen': datetime.now().strftime('%Y-%m-%d'),
    'canonical_model_status': 'CANONICAL_FROZEN_V7C',
    'esp32_status': 'NOT_YET_EXECUTED',
    'v7c_validated_on_esp32': False,
    'golden_samples': 20,
    'extended_samples': 120,
    'saturation_cases': 6,
    'anomaly_scenarios': 10,
    'serial_schema': 'sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status',
    'serial_schema_fields': 10,
    'required_return_files': [
        'v8b2_esp32_golden_log.txt',
        'v8b2_esp32_extended_log.txt',
        'v8b2_esp32_anomaly_log.txt',
        'v8b2_validation_metrics.json',
        'v8b2_golden_comparison.csv',
        'v8b2_extended_comparison.csv',
        'v8b2_anomaly_comparison.csv',
        'v8b2_validation_report.md',
        'RESULT_TEMPLATE_ESP32_V8B2_CANONICAL.md (preenchido)',
    ],
    'acceptance_criteria': {
        'GOLDEN_MAE': '< 0.001',
        'GOLDEN_R2': '> 0.99',
        'EXTENDED_MAE_non_saturated': '< 0.001',
        'EXTENDED_WARN_SAT_count': '6 expected',
        'ANOMALY_recall_embedded': '>= 0.90',
        'crashes_resets': '== 0',
        'mean_latency_ms': '< 0.5 (WARN if exceeded)',
        'min_free_heap_bytes': '> 280000 (WARN if below)',
    },
    'limitations': [
        'V7C has NOT been validated on ESP32 hardware -- this is preparation for that test',
        'Anomaly detection rules are Phase 1 heuristics (thresholds) -- not ML-based',
        'No field operation with real battery sensors',
        '6 saturated samples in extended replay -- clipping to [0,1] is expected behavior',
        'Validator GOLDEN merge uses sample_id-based join -- may fail to match int vs string IDs (V8B3 audit finding)',
        'Stress test (1000+ iterations) planned for V8C after V8B2 hardware results',
    ],
    'v8b3_audit_findings': {
        'total_checks': len(audit_rows),
        'passed': len(audit_rows) - n_fail,
        'failed': n_fail,
        'missing_required_files': n_missing,
        'validator_golden_merge_bug': validator_golden_merge_issue,
    },
    'blockers': blockers,
    'ready_to_zip': ready_to_zip,
    'ready_to_zip_note': 'Package files present; validator GOLDEN merge fix recommended before hardware run',
}

lm_path = os.path.join(OUTDIR, 'v8b3_package_lock_manifest.json')
with open(lm_path, 'w', encoding='utf-8') as f:
    json.dump(lock, f, indent=2, ensure_ascii=False)
print(f'  ready_to_zip: {ready_to_zip}')
print(f'  blockers: {blockers}')
print(f'Saved: {lm_path}')

print('\n=== V8B3 Audit Script Complete ===')
print(f'Output dir: {OUTDIR}')
