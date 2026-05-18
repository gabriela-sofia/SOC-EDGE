"""
V8B3 test suite: handoff package freeze audit validation.

Tests:
  1.  Package inventory CSV exists and has 0 missing required files
  2.  Checksums CSV exists and covers key files
  3.  Consistency audit CSV exists
  4.  V8B3 lock manifest exists with correct structure
  5.  Scientific report V8B3 exists
  6.  Zip instruction file exists
  7.  Final message for ESP32 exists
  8.  Serial schema 10 fields in freeze manifest
  9.  MAE threshold appears in freeze manifest criteria
 10.  Anomaly recall threshold appears in freeze manifest
 11.  No claim V7C already validated on ESP32 in any V8B3 doc
 12.  No field validation claim in V8B3 docs
 13.  No instruction to swap ESP32 board in V8B3 docs
 14.  Lock manifest ready_to_zip is True (no blockers blocking zip)
 15.  Dry-run metrics exist and GOLDEN/EXTENDED passed
 16.  Dry-run ANOMALY passed after validator fix
 17.  Validator GOLDEN merge fix applied (no sample_id string join)
 18.  Validator ANOMALY recall fix applied (uses embedded_indices)
 19.  V8B2 validator dry-run overall status is PASS in metrics JSON
"""

import os
import json
import csv
import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FREEZE_DIR = os.path.join(BASE, 'outputs', 'v8b3_handoff_freeze')
HANDOFF = os.path.join(BASE, 'handoff_esp32_v8b2_canonical')
REPORTS = os.path.join(BASE, 'REPORTS')
VALIDATOR = os.path.join(HANDOFF, 'validation', 'validate_esp32_v8b2.py')

V8B3_REPORT = os.path.join(REPORTS, 'V8B3_HANDOFF_PACKAGE_FREEZE_AND_DELIVERY_LOCK.md')
LOCK_MANIFEST = os.path.join(FREEZE_DIR, 'v8b3_package_lock_manifest.json')
DRY_RUN_METRICS = os.path.join(FREEZE_DIR, 'v8b3_validator_dry_run_metrics.json')

_V8B3_DOCS = [
    V8B3_REPORT,
    os.path.join(HANDOFF, 'COMO_ZIPAR_E_ENVIAR.md'),
    os.path.join(HANDOFF, 'MENSAGEM_FINAL_PARA_ENVIO_ESP32.md'),
    LOCK_MANIFEST,
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def lock_manifest():
    with open(LOCK_MANIFEST, encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def dry_run_metrics():
    with open(DRY_RUN_METRICS, encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def validator_source():
    with open(VALIDATOR, encoding='utf-8') as f:
        return f.read()


# ---------------------------------------------------------------------------
# Tests 1-3: Audit output files
# ---------------------------------------------------------------------------

def test_inventory_csv_exists_with_no_missing_required():
    path = os.path.join(FREEZE_DIR, 'v8b3_package_inventory.csv')
    assert os.path.exists(path), f"Inventory CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 20, f"Expected >= 20 inventory rows, got {len(rows)}"
    missing = [r for r in rows if r.get('status', '').startswith('MISSING_REQUIRED')]
    assert len(missing) == 0, (
        f"Missing required files: {[r['path'] for r in missing]}"
    )


def test_checksums_csv_exists_and_covers_key_files():
    path = os.path.join(FREEZE_DIR, 'v8b3_package_checksums.csv')
    assert os.path.exists(path), f"Checksums CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 10, f"Expected >= 10 checksum rows, got {len(rows)}"
    # All rows should have status OK
    for row in rows:
        assert row.get('status') == 'OK', (
            f"File has non-OK checksum status: {row.get('path')} -> {row.get('status')}"
        )
    # sha256 must not be placeholder
    for row in rows:
        sha = row.get('sha256', '')
        assert len(sha) == 64, (
            f"Invalid sha256 for {row.get('path')}: {sha!r}"
        )


def test_consistency_audit_csv_exists():
    path = os.path.join(FREEZE_DIR, 'v8b3_consistency_audit.csv')
    assert os.path.exists(path), f"Consistency audit CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 15, f"Expected >= 15 audit checks, got {len(rows)}"


# ---------------------------------------------------------------------------
# Tests 4-7: Documentation files
# ---------------------------------------------------------------------------

def test_v8b3_lock_manifest_exists(lock_manifest):
    assert os.path.exists(LOCK_MANIFEST), f"Lock manifest not found: {LOCK_MANIFEST}"
    required_keys = [
        'package_name', 'package_version', 'golden_samples', 'extended_samples',
        'saturation_cases', 'anomaly_scenarios', 'serial_schema',
        'v7c_validated_on_esp32', 'ready_to_zip', 'acceptance_criteria',
    ]
    for key in required_keys:
        assert key in lock_manifest, f"Lock manifest missing key: {key}"


def test_scientific_report_v8b3_exists():
    assert os.path.exists(V8B3_REPORT), f"V8B3 scientific report not found: {V8B3_REPORT}"
    content = open(V8B3_REPORT, encoding='utf-8').read()
    assert 'V8B3' in content, "Report missing V8B3 reference"
    assert 'V8A' in content, "Report missing V8A baseline reference"
    assert 'PASS' in content, "Report missing PASS status reference"
    assert len(content) > 2000, "Report seems too short"


def test_zip_instruction_file_exists():
    path = os.path.join(HANDOFF, 'COMO_ZIPAR_E_ENVIAR.md')
    assert os.path.exists(path), f"Zip instructions not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'zip' in content.lower() or 'Compress' in content, "Zip instructions missing zip command"
    assert 'results_template' in content or 'template' in content.lower(), (
        "Zip instructions missing return template reference"
    )


def test_final_message_for_esp32_exists():
    path = os.path.join(HANDOFF, 'MENSAGEM_FINAL_PARA_ENVIO_ESP32.md')
    assert os.path.exists(path), f"Final message not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'GOLDEN' in content, "Final message missing GOLDEN mode"
    assert 'EXTENDED' in content, "Final message missing EXTENDED mode"
    assert 'ANOMALY' in content, "Final message missing ANOMALY mode"
    assert 'mA' in content, "Final message missing current unit warning"
    assert len(content) > 300, "Final message seems too short"


# ---------------------------------------------------------------------------
# Tests 8-10: Thresholds in lock manifest
# ---------------------------------------------------------------------------

def test_serial_schema_10_fields_in_lock_manifest(lock_manifest):
    schema = lock_manifest.get('serial_schema', '')
    fields = [f.strip() for f in schema.split(',')]
    assert len(fields) == 10, f"Expected 10 schema fields, got {len(fields)}"
    expected = ['sample_id', 'mode', 'soc_final', 'inference_time_ms', 'free_heap',
                'min_free_heap', 'max_alloc_heap', 'anomaly_flag', 'anomaly_code', 'status']
    for field in expected:
        assert field in fields, f"Schema missing field: {field}"


def test_mae_threshold_in_lock_manifest_criteria(lock_manifest):
    criteria = lock_manifest.get('acceptance_criteria', {})
    mae_val = criteria.get('GOLDEN_MAE', '')
    assert '0.001' in mae_val, (
        f"MAE threshold 0.001 not in acceptance_criteria.GOLDEN_MAE: {mae_val!r}"
    )


def test_anomaly_recall_threshold_in_lock_manifest_criteria(lock_manifest):
    criteria = lock_manifest.get('acceptance_criteria', {})
    recall_val = criteria.get('ANOMALY_recall_embedded', '')
    assert '0.90' in recall_val or '>= 0.90' in recall_val or '0.9' in recall_val, (
        f"Recall threshold not in acceptance_criteria.ANOMALY_recall_embedded: {recall_val!r}"
    )


# ---------------------------------------------------------------------------
# Tests 11-13: Scientific integrity
# ---------------------------------------------------------------------------

def _read_doc(path):
    if not os.path.exists(path):
        return ''
    return open(path, encoding='utf-8').read()


def test_no_v7c_validated_on_esp32_claim_in_v8b3_docs():
    forbidden = [
        'v7c validated on esp32',
        'v7c foi validado na esp32',
        'canonical validated on hardware',
        'v7c on esp32 confirmed',
    ]
    for doc_path in _V8B3_DOCS:
        content = _read_doc(doc_path).lower()
        doc_name = os.path.basename(doc_path)
        for phrase in forbidden:
            idx = content.find(phrase)
            if idx < 0:
                continue
            context = content[max(0, idx-50):idx+len(phrase)+50]
            negated = (
                'not yet' in context or 'has not' in context or
                '[fail]' in context or 'not been' in context or
                'nao foi' in context or 'pending' in context
            )
            assert negated, (
                f"Positive V7C-on-ESP32 claim in {doc_name}: '{phrase}'\nContext: {context}"
            )


def test_no_field_validation_claim_in_v8b3_docs():
    forbidden = [
        'field validated',
        'field validation complete',
        'validated in the field',
        'validacao de campo concluida',
    ]
    for doc_path in _V8B3_DOCS:
        content = _read_doc(doc_path).lower()
        doc_name = os.path.basename(doc_path)
        for phrase in forbidden:
            idx = content.find(phrase)
            if idx < 0:
                continue
            context = content[max(0, idx-40):idx+len(phrase)+40]
            negated = 'not' in context or '[fail]' in context or 'nao' in context
            assert negated, (
                f"Field validation claim in {doc_name}: '{phrase}'\nContext: {context}"
            )


def test_no_swap_esp32_instruction_in_v8b3_docs():
    forbidden = [
        'trocar a placa',
        'swap the board',
        'use a different board',
        'replace the esp32',
    ]
    for doc_path in _V8B3_DOCS:
        content = _read_doc(doc_path).lower()
        doc_name = os.path.basename(doc_path)
        for phrase in forbidden:
            idx = content.find(phrase)
            if idx < 0:
                continue
            context = content[max(0, idx-30):idx+len(phrase)+30]
            negated = 'nao trocar' in context or 'not swap' in context or 'nao' in context
            assert negated, (
                f"Swap instruction in {doc_name}: '{phrase}'\nContext: {context}"
            )


# ---------------------------------------------------------------------------
# Test 14: ready_to_zip = True in lock manifest
# ---------------------------------------------------------------------------

def test_lock_manifest_ready_to_zip_is_true(lock_manifest):
    rtzip = lock_manifest.get('ready_to_zip')
    assert rtzip is True, (
        f"ready_to_zip should be True, got: {rtzip!r}\nblockers: {lock_manifest.get('blockers')}"
    )


# ---------------------------------------------------------------------------
# Tests 15-16: Dry-run results
# ---------------------------------------------------------------------------

def test_dry_run_metrics_exist_and_golden_extended_pass(dry_run_metrics):
    golden = dry_run_metrics.get('golden', {})
    extended = dry_run_metrics.get('extended', {})
    assert golden.get('status') == 'PASS', (
        f"Dry-run GOLDEN not PASS: {golden.get('status')}, MAE={golden.get('mae')}"
    )
    assert extended.get('status') == 'PASS', (
        f"Dry-run EXTENDED not PASS: {extended.get('status')}, MAE={extended.get('mae_non_saturated')}"
    )
    assert golden.get('mae', 1) < 0.001, f"Dry-run GOLDEN MAE too high: {golden.get('mae')}"
    assert extended.get('mae_non_saturated', 1) < 0.001, (
        f"Dry-run EXTENDED MAE non-saturated too high: {extended.get('mae_non_saturated')}"
    )
    assert extended.get('n_saturated') == 6, (
        f"Expected 6 saturated in dry-run, got {extended.get('n_saturated')}"
    )


def test_dry_run_anomaly_pass_after_validator_fix(dry_run_metrics):
    anomaly = dry_run_metrics.get('anomaly', {})
    assert anomaly.get('status') == 'PASS', (
        f"Dry-run ANOMALY not PASS: recall_embedded={anomaly.get('recall_embedded')}"
    )
    assert anomaly.get('recall_embedded', 0) >= 0.90, (
        f"Dry-run recall_embedded below 0.90: {anomaly.get('recall_embedded')}"
    )


# ---------------------------------------------------------------------------
# Tests 17-18: Validator bug fixes applied
# ---------------------------------------------------------------------------

def test_validator_golden_merge_uses_positional_not_string_join(validator_source):
    # After fix: validate_golden uses ref_idx positional merge, not sample_id string join
    assert "left_on='sample_id'" not in validator_source, (
        "Validator GOLDEN merge still uses sample_id string join -- fix not applied"
    )
    # Should have positional merge
    assert 'ref_idx' in validator_source, (
        "Validator does not use ref_idx positional merge for GOLDEN"
    )


def test_validator_anomaly_recall_uses_embedded_indices(validator_source):
    # After fix: uses embedded_indices list, not head slice
    assert 'embedded_indices' in validator_source, (
        "Validator does not use embedded_indices for recall computation"
    )
    # Should NOT have the old head-slice pattern
    assert 'obs_flags[:n_emb]' not in validator_source, (
        "Validator still uses obs_flags[:n_emb] head slice -- fix not applied"
    )


# ---------------------------------------------------------------------------
# Test 19: Overall dry-run PASS
# ---------------------------------------------------------------------------

def test_dry_run_overall_status_is_pass(dry_run_metrics):
    # All three modes must have passed
    for mode in ['golden', 'extended', 'anomaly']:
        status = dry_run_metrics.get(mode, {}).get('status', 'MISSING')
        assert status == 'PASS', f"Dry-run mode {mode.upper()} is not PASS: {status}"
    # Resources check
    resources = dry_run_metrics.get('resources', {})
    assert resources.get('crash_detected') is False, "Dry-run shows crash"
    assert resources.get('latency_warn') is False, "Dry-run latency warning triggered"
