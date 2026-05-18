"""
V8B2 test suite: canonical ESP32 handoff package validation.

Tests:
  1.  Handoff folder exists
  2.  Firmware .ino exists
  3.  C header (model weights) exists
  4.  Replay C header (vectors) exists
  5.  Model manifest exists
  6.  Golden replay CSV exists
  7.  Extended replay CSV exists (120 samples)
  8.  Extended reference CSV exists
  9.  Saturation cases CSV exists (>= 3 saturated)
 10.  Anomaly scenarios CSV exists (10 scenarios)
 11.  Anomaly expected flags CSV exists
 12.  Python validator exists
 13.  Results template exists
 14.  LEIA_PRIMEIRO guide exists
 15.  Message for ESP32 person exists
 16.  Scientific report exists
 17.  Lock manifest exists with correct structure
 18.  Serial schema (10 fields) documented in README and validator
 19.  MAE threshold < 0.001 present in validator
 20.  Anomaly recall threshold >= 0.90 present in validator
 21.  No claim that V7C is already validated on ESP32 hardware
 22.  No claim of field validation
 23.  No recommendation to swap ESP32 board
 24.  Lock manifest flags esp32_validated = false
 25.  Saturation clipping documented in firmware
"""

import os
import json
import csv
import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(BASE, 'handoff_esp32_v8b2_canonical')
FIRMWARE = os.path.join(HANDOFF, 'firmware')
MODEL = os.path.join(HANDOFF, 'model')
REPLAY = os.path.join(HANDOFF, 'replay')
ANOMALY_DIR = os.path.join(HANDOFF, 'anomaly')
VALIDATION = os.path.join(HANDOFF, 'validation')
RESULTS_TEMPLATE = os.path.join(HANDOFF, 'results_template')
REPORTS = os.path.join(BASE, 'REPORTS')
OUTPUTS = os.path.join(BASE, 'outputs', 'v8b2_handoff_package')

LOCK_MANIFEST = os.path.join(OUTPUTS, 'v8b2_package_lock_manifest.json')
SCIENTIFIC_REPORT = os.path.join(REPORTS, 'V8B2_CANONICAL_EXTENDED_REPLAY_ANOMALY_AND_STRESS_HANDOFF_PACKAGE.md')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def lock_manifest():
    with open(LOCK_MANIFEST, encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def scientific_report():
    with open(SCIENTIFIC_REPORT, encoding='utf-8') as f:
        return f.read()


@pytest.fixture(scope='module')
def validator_source():
    path = os.path.join(VALIDATION, 'validate_esp32_v8b2.py')
    with open(path, encoding='utf-8') as f:
        return f.read()


@pytest.fixture(scope='module')
def readme_content():
    with open(os.path.join(HANDOFF, 'README.md'), encoding='utf-8') as f:
        return f.read()


# ---------------------------------------------------------------------------
# Tests 1-4: Firmware files
# ---------------------------------------------------------------------------

def test_handoff_folder_exists():
    assert os.path.isdir(HANDOFF), f"Handoff folder not found: {HANDOFF}"


def test_firmware_ino_exists():
    path = os.path.join(FIRMWARE, 'firmware_soc_v8b2_canonical.ino')
    assert os.path.exists(path), f"Firmware .ino not found: {path}"
    size = os.path.getsize(path)
    assert size > 5000, f"Firmware file seems too small: {size} bytes"


def test_model_weights_header_exists():
    path = os.path.join(FIRMWARE, 'canonical_model_weights_v8b2.h')
    assert os.path.exists(path), f"Model weights header not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'V8B2' in content or 'v8b2' in content.lower(), "Header missing V8B2 marker"
    assert 'float' in content.lower(), "Header missing float arrays"


def test_replay_vectors_header_exists():
    path = os.path.join(FIRMWARE, 'replay_vectors_v8b2.h')
    assert os.path.exists(path), f"Replay vectors header not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'GOLDEN_VECTORS' in content, "Header missing GOLDEN_VECTORS"
    assert 'EXTENDED_VECTORS' in content, "Header missing EXTENDED_VECTORS"
    assert 'ANOMALY_VECTORS' in content, "Header missing ANOMALY_VECTORS"


# ---------------------------------------------------------------------------
# Tests 5-9: Model and replay files
# ---------------------------------------------------------------------------

def test_model_manifest_exists():
    path = os.path.join(MODEL, 'MODEL_MANIFEST_V8B2.md')
    assert os.path.exists(path), f"Model manifest not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'V7C' in content, "Manifest missing V7C model reference"
    assert 'mA' in content, "Manifest missing current unit (mA)"
    assert len(content) > 500, "Model manifest seems too short"


def test_golden_replay_exists():
    path = os.path.join(REPLAY, 'canonical_golden_vectors_v8b2.csv')
    assert os.path.exists(path), f"Golden replay CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 20, f"Expected 20 golden vectors, got {len(rows)}"


def test_extended_replay_exists_with_120_samples():
    path = os.path.join(REPLAY, 'canonical_extended_replay_v8b2.csv')
    assert os.path.exists(path), f"Extended replay CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 120, f"Expected 120 extended samples, got {len(rows)}"


def test_extended_reference_csv_exists():
    path = os.path.join(REPLAY, 'canonical_extended_reference_v8b2.csv')
    assert os.path.exists(path), f"Extended reference CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 120, f"Extended reference should have 120 rows, got {len(rows)}"
    # Must have clipped reference column
    assert 'soc_clipped_reference' in rows[0], (
        f"soc_clipped_reference column missing. Got: {list(rows[0].keys())}"
    )


def test_saturation_cases_exist_with_minimum_count():
    path = os.path.join(REPLAY, 'canonical_saturation_cases_v8b2.csv')
    assert os.path.exists(path), f"Saturation cases CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 3, f"Expected >= 3 saturated cases, got {len(rows)}"
    # Each row must have saturation direction
    for row in rows:
        keys = list(row.keys())
        assert any('sat' in k.lower() or 'clip' in k.lower() for k in keys), (
            f"Saturation case row missing saturation info: {keys}"
        )


# ---------------------------------------------------------------------------
# Tests 10-12: Anomaly files
# ---------------------------------------------------------------------------

def test_anomaly_scenarios_exist_with_10_entries():
    path = os.path.join(ANOMALY_DIR, 'anomaly_replay_scenarios_v8b2.csv')
    assert os.path.exists(path), f"Anomaly scenarios CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 10, f"Expected 10 anomaly scenarios, got {len(rows)}"


def test_anomaly_expected_flags_exist():
    path = os.path.join(ANOMALY_DIR, 'anomaly_expected_flags_v8b2.csv')
    assert os.path.exists(path), f"Anomaly expected flags CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 10, f"Expected 10 flag rows, got {len(rows)}"
    # Each row must have an expected_anomaly_flag column
    for row in rows:
        assert 'expected_anomaly_flag' in row, (
            f"expected_anomaly_flag column missing. Got: {list(row.keys())}"
        )


def test_anomaly_manifest_exists():
    path = os.path.join(ANOMALY_DIR, 'anomaly_manifest_v8b2.csv')
    assert os.path.exists(path), f"Anomaly manifest CSV not found: {path}"
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 10, f"Expected >= 10 manifest rows, got {len(rows)}"


# ---------------------------------------------------------------------------
# Tests 13-16: Documentation files
# ---------------------------------------------------------------------------

def test_python_validator_exists():
    path = os.path.join(VALIDATION, 'validate_esp32_v8b2.py')
    assert os.path.exists(path), f"Python validator not found: {path}"
    size = os.path.getsize(path)
    assert size > 3000, f"Validator seems too small: {size} bytes"


def test_results_template_exists():
    path = os.path.join(RESULTS_TEMPLATE, 'RESULT_TEMPLATE_ESP32_V8B2_CANONICAL.md')
    assert os.path.exists(path), f"Results template not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'MAE' in content, "Results template missing MAE field"
    assert 'GOLDEN' in content, "Results template missing GOLDEN mode"
    assert 'EXTENDED' in content, "Results template missing EXTENDED mode"
    assert 'ANOMALY' in content, "Results template missing ANOMALY mode"


def test_leia_primeiro_guide_exists():
    path = os.path.join(HANDOFF, 'LEIA_PRIMEIRO_ESP32.md')
    assert os.path.exists(path), f"LEIA_PRIMEIRO guide not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'GOLDEN' in content, "Guide missing GOLDEN mode explanation"
    assert 'EXTENDED' in content, "Guide missing EXTENDED mode explanation"
    assert 'validador' in content.lower() or 'validator' in content.lower(), (
        "Guide missing validator instructions"
    )
    assert len(content) > 1000, "LEIA_PRIMEIRO guide seems too short"


def test_message_for_esp32_person_exists():
    path = os.path.join(HANDOFF, 'MENSAGEM_PARA_PESSOA_DA_ESP_V8B2.md')
    assert os.path.exists(path), f"Message for ESP person not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert len(content) > 100, "Message seems too short"
    # Must mention the firmware file
    assert 'firmware' in content.lower() or '.ino' in content.lower(), (
        "Message missing firmware reference"
    )


# ---------------------------------------------------------------------------
# Test 17: Lock manifest structure
# ---------------------------------------------------------------------------

def test_lock_manifest_has_correct_structure(lock_manifest):
    required_keys = [
        'package_version', 'canonical_model_version', 'golden_samples',
        'extended_samples', 'anomaly_scenarios', 'serial_schema',
        'soc_acceptance_mae', 'anomaly_acceptance_recall',
        'esp32_validated', 'ready_for_future_handoff', 'limitations',
    ]
    for key in required_keys:
        assert key in lock_manifest, f"Lock manifest missing key: {key}"

    assert lock_manifest['golden_samples'] == 20, (
        f"Expected 20 golden samples, got {lock_manifest['golden_samples']}"
    )
    assert lock_manifest['extended_samples'] == 120, (
        f"Expected 120 extended samples, got {lock_manifest['extended_samples']}"
    )
    assert lock_manifest['anomaly_scenarios'] == 10, (
        f"Expected 10 anomaly scenarios, got {lock_manifest['anomaly_scenarios']}"
    )
    assert lock_manifest['soc_acceptance_mae'] <= 0.001, (
        f"MAE threshold too loose: {lock_manifest['soc_acceptance_mae']}"
    )
    assert lock_manifest['anomaly_acceptance_recall'] >= 0.90, (
        f"Recall threshold too loose: {lock_manifest['anomaly_acceptance_recall']}"
    )


# ---------------------------------------------------------------------------
# Test 18: Serial schema documented (10 fields)
# ---------------------------------------------------------------------------

def test_serial_schema_10_fields_in_readme(readme_content):
    schema = 'sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status'
    assert schema in readme_content, (
        "10-field serial schema not found in README.md"
    )


def test_serial_schema_10_fields_in_lock_manifest(lock_manifest):
    schema = lock_manifest.get('serial_schema', '')
    fields = [f.strip() for f in schema.split(',')]
    assert len(fields) == 10, f"Expected 10 schema fields, got {len(fields)}: {fields}"
    expected = ['sample_id', 'mode', 'soc_final', 'inference_time_ms', 'free_heap',
                'min_free_heap', 'max_alloc_heap', 'anomaly_flag', 'anomaly_code', 'status']
    for field in expected:
        assert field in fields, f"Schema missing field: {field}"


# ---------------------------------------------------------------------------
# Tests 19-20: Thresholds in validator
# ---------------------------------------------------------------------------

def test_mae_threshold_in_validator(validator_source):
    # Validator must reference 0.001 as the MAE threshold
    assert '0.001' in validator_source, (
        "MAE threshold 0.001 not found in validator source"
    )


def test_anomaly_recall_threshold_in_validator(validator_source):
    # Validator must reference 0.90 as recall threshold
    has_90 = '0.90' in validator_source or '0.9' in validator_source
    assert has_90, "Recall threshold 0.90 not found in validator source"


# ---------------------------------------------------------------------------
# Tests 21-23: Scientific integrity -- no false claims
# ---------------------------------------------------------------------------

_DOCS_TO_CHECK = [
    os.path.join(HANDOFF, 'README.md'),
    os.path.join(HANDOFF, 'LEIA_PRIMEIRO_ESP32.md'),
    os.path.join(HANDOFF, 'MENSAGEM_PARA_PESSOA_DA_ESP_V8B2.md'),
    os.path.join(MODEL, 'MODEL_MANIFEST_V8B2.md'),
    SCIENTIFIC_REPORT,
]


def _read_doc(path):
    if not os.path.exists(path):
        return ''
    return open(path, encoding='utf-8').read()


def test_no_claim_v7c_already_validated_on_esp32():
    """No document should positively assert that V7C was already validated on hardware."""
    forbidden_positive = [
        'v7c validated on esp32',
        'v7c foi validado na esp32',
        'canonical model validated on esp32',
        'canonical validated on hardware',
    ]
    for doc_path in _DOCS_TO_CHECK:
        content = _read_doc(doc_path).lower()
        doc_name = os.path.basename(doc_path)
        for phrase in forbidden_positive:
            idx = content.find(phrase)
            if idx < 0:
                continue
            # Allow if the phrase appears only as a forbidden claim (preceded by [fail], not, (not)
            context = content[max(0, idx - 50):idx + len(phrase) + 50]
            negated = (
                '[fail]' in context or
                'not yet' in context or
                'not been' in context or
                'has not' in context or
                '(not' in context or
                'nao foi' in context or
                'ainda nao' in context or
                'pending' in context
            )
            assert negated, (
                f"Positive V7C-on-ESP32 claim found in {doc_name}: '{phrase}'\nContext: {context}"
            )


def test_no_field_validation_claim():
    """No document should positively claim field validation was done."""
    forbidden = [
        'field validated',
        'field validation complete',
        'validated in field',
        'validacao de campo concluida',
        'validado em campo',
    ]
    for doc_path in _DOCS_TO_CHECK:
        content = _read_doc(doc_path).lower()
        doc_name = os.path.basename(doc_path)
        for phrase in forbidden:
            idx = content.find(phrase)
            if idx < 0:
                continue
            context = content[max(0, idx - 50):idx + len(phrase) + 50]
            negated = (
                '[fail]' in context or
                'not' in context or
                'nao' in context or
                'pending' in context
            )
            assert negated, (
                f"Field validation claim found in {doc_name}: '{phrase}'\nContext: {context}"
            )


def test_no_recommendation_to_swap_esp32_board():
    """No document should recommend swapping the ESP32 board."""
    forbidden = [
        'trocar a placa',
        'swap the board',
        'use a different board',
        'replace the esp32',
        'substituir a esp32',
    ]
    for doc_path in _DOCS_TO_CHECK:
        content = _read_doc(doc_path).lower()
        doc_name = os.path.basename(doc_path)
        for phrase in forbidden:
            idx = content.find(phrase)
            if idx < 0:
                continue
            # Allow only if explicitly negated (e.g. "Nao trocar a placa")
            context = content[max(0, idx - 30):idx + len(phrase) + 30]
            negated = (
                'nao trocar' in context or
                'not swap' in context or
                'do not' in context or
                'never' in context or
                'nao' in context
            )
            assert negated, (
                f"Board swap recommendation in {doc_name}: '{phrase}'\nContext: {context}"
            )


# ---------------------------------------------------------------------------
# Test 24: Lock manifest flags esp32_validated = false
# ---------------------------------------------------------------------------

def test_lock_manifest_esp32_validated_is_false(lock_manifest):
    val = lock_manifest.get('esp32_validated')
    assert val is False, (
        f"esp32_validated should be False (boolean), got: {val!r}"
    )


# ---------------------------------------------------------------------------
# Test 25: Clipping documented in firmware
# ---------------------------------------------------------------------------

def test_firmware_documents_clipping():
    path = os.path.join(FIRMWARE, 'firmware_soc_v8b2_canonical.ino')
    content = open(path, encoding='utf-8').read()
    # clip / fmaxf / fminf or min/max pattern
    has_clip = (
        'clip' in content.lower() or
        'fmaxf' in content or
        'fminf' in content or
        ('0.0f' in content and '1.0f' in content)
    )
    assert has_clip, "Firmware does not appear to implement SOC clipping to [0, 1]"
