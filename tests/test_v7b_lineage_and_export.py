"""
Tests for V7B Model Lineage Audit, Export Gate, and Golden Vectors.
"""

import csv
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'outputs', 'v7_edge_ready_offline')
ARTIFACTS = os.path.join(BASE, 'artifacts', 'edge_v7')
REPORTS = os.path.join(BASE, 'REPORTS')


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _load_csv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


# --- Test 1: All V7B files exist ---
def test_v7b_required_files_exist():
    required = [
        os.path.join(OUT, 'v7b_model_lineage_audit.csv'),
        os.path.join(OUT, 'v7b_model_lineage_decision.json'),
        os.path.join(OUT, 'v7b_feature_lineage_check.csv'),
        os.path.join(ARTIFACTS, 'golden_vectors.csv'),
        os.path.join(ARTIFACTS, 'golden_vectors_expected_serial_output.csv'),
        os.path.join(OUT, 'v7b_export_gate_report.md'),
        os.path.join(ARTIFACTS, 'model_weights.json'),
        os.path.join(ARTIFACTS, 'model_weights_preview.h'),
        os.path.join(REPORTS, 'V7B_MODEL_LINEAGE_AUDIT_AND_EXPORT_GATE.md'),
    ]
    missing = [p for p in required if not os.path.exists(p)]
    assert not missing, 'Missing V7B files:\n' + '\n'.join(missing)


# --- Test 2: Lineage audit has required items ---
def test_v7b_lineage_audit_has_required_items():
    rows = _load_csv(os.path.join(OUT, 'v7b_model_lineage_audit.csv'))
    items = {r['item'] for r in rows}
    required_items = ['target_column', 'method_b_confirmed', 'model_class',
                      'features_in_model', 'scaler_confirmed', 'r2_reported']
    for item in required_items:
        assert item in items, 'Lineage audit missing item: {}'.format(item)


# --- Test 3: Lineage decision confirms Method B target ---
def test_v7b_decision_confirms_method_b():
    d = _load_json(os.path.join(OUT, 'v7b_model_lineage_decision.json'))
    assert d['method_b_confirmed'] is True, \
        'Lineage decision must confirm method_b_confirmed=true'
    assert d['target_confirmed'] is True, \
        'Lineage decision must confirm target_confirmed=true'
    assert 'soc_method_b' in d.get('target_value', '').lower() or \
           'method_b' in d.get('target_value', '').lower(), \
        'target_value must reference soc_method_b'


# --- Test 4: Lineage decision has correct model_status ---
def test_v7b_decision_model_status():
    d = _load_json(os.path.join(OUT, 'v7b_model_lineage_decision.json'))
    valid_statuses = {'APPROVED_FOR_EDGE_HANDOFF', 'LEGACY_MODEL_WARN', 'LINEAGE_BLOCKED'}
    assert d['model_status'] in valid_statuses, \
        'model_status must be one of {}, got: {}'.format(valid_statuses, d['model_status'])


# --- Test 5: If handoff_allowed, there must be explicit limitation or approval ---
def test_v7b_handoff_allowed_has_conditions():
    d = _load_json(os.path.join(OUT, 'v7b_model_lineage_decision.json'))
    if d.get('handoff_allowed') is True:
        has_condition = bool(d.get('handoff_condition')) or bool(d.get('limitations'))
        assert has_condition, \
            'handoff_allowed=true requires either handoff_condition or limitations to be documented'


# --- Test 6: Feature lineage check covers all 6 features ---
def test_v7b_feature_lineage_has_6_features():
    rows = _load_csv(os.path.join(OUT, 'v7b_feature_lineage_check.csv'))
    model_features = [r['feature_name'] for r in rows if r.get('in_model', '').lower() == 'true']
    assert len(model_features) == 6, \
        'Feature lineage must document exactly 6 features in model, got {}'.format(len(model_features))
    expected = ['voltage_v', 'temperature_c', 'current_ma',
                'delta_voltage', 'delta_temperature', 'delta_current']
    for feat in expected:
        assert feat in model_features, \
            'Feature {} missing from model features list'.format(feat)


# --- Test 7: Feature lineage documents PLANNED features separately ---
def test_v7b_feature_lineage_documents_planned():
    rows = _load_csv(os.path.join(OUT, 'v7b_feature_lineage_check.csv'))
    planned = [r for r in rows if 'PLANNED' in r.get('status', '').upper()]
    assert len(planned) >= 1, \
        'Feature lineage must document at least 1 PLANNED_NOT_IN_MODEL feature'


# --- Test 8: Golden vectors has 20 rows with required columns ---
def test_v7b_golden_vectors_complete():
    rows = _load_csv(os.path.join(ARTIFACTS, 'golden_vectors.csv'))
    assert len(rows) == 20, 'Expected 20 golden vectors, got {}'.format(len(rows))
    required_cols = ['sample_id', 'voltage_v', 'temperature_c', 'current_ma',
                     'soc_sklearn', 'soc_numpy', 'abs_diff', 'status']
    if rows:
        for col in required_cols:
            assert col in rows[0], 'Golden vectors missing column: {}'.format(col)


# --- Test 9: All golden vectors have PASS_EXACT status ---
def test_v7b_golden_vectors_all_pass():
    rows = _load_csv(os.path.join(ARTIFACTS, 'golden_vectors.csv'))
    failures = [r for r in rows if r.get('status') != 'PASS_EXACT']
    assert not failures, \
        '{} golden vectors do not have PASS_EXACT status: {}'.format(
            len(failures), [r['sample_id'] for r in failures])


# --- Test 10: Golden vectors expected serial output has correct columns ---
def test_v7b_golden_serial_output_complete():
    rows = _load_csv(os.path.join(ARTIFACTS, 'golden_vectors_expected_serial_output.csv'))
    assert len(rows) == 20, 'Expected 20 serial output rows'
    required_cols = ['sample_id', 'soc_predicted', 'anomaly_flag', 'anomaly_reason']
    if rows:
        for col in required_cols:
            assert col in rows[0], 'Serial output missing column: {}'.format(col)


# --- Test 11: Model weights JSON has complete layer structure ---
def test_v7b_model_weights_json_complete():
    d = _load_json(os.path.join(ARTIFACTS, 'model_weights.json'))
    assert 'layers' in d, 'model_weights.json must have layers key'
    assert len(d['layers']) == 3, 'Expected 3 layers, got {}'.format(len(d['layers']))
    for layer in d['layers']:
        assert 'weights' in layer and 'biases' in layer, \
            'Layer {} missing weights or biases'.format(layer.get('layer_index'))
        assert layer['input_size'] > 0 and layer['output_size'] > 0, \
            'Layer sizes must be positive'
    total = d.get('total_parameters', 0)
    assert total == 2561, 'Total parameters must be 2561, got {}'.format(total)


# --- Test 12: C header preview contains all required sections ---
def test_v7b_c_header_preview_structure():
    content = _read(os.path.join(ARTIFACTS, 'model_weights_preview.h'))
    required = ['MLP_INPUT_SIZE', 'SCALER_MIN', 'SCALER_SCALE',
                'W0', 'B0', 'W1', 'B1', 'W2', 'B2', 'ReLU', '#ifndef']
    for item in required:
        assert item in content, \
            'C header preview missing: {}'.format(item)


# --- Test 13: Export gate report classifies correctly ---
def test_v7b_export_gate_classification():
    content = _read(os.path.join(OUT, 'v7b_export_gate_report.md'))
    valid_classifications = ['TFLITE_READY', 'MANUAL_C_INFERENCE_RECOMMENDED',
                             'RETRAIN_KERAS_EQUIVALENT_REQUIRED', 'EXPORT_BLOCKED']
    has_classification = any(c in content for c in valid_classifications)
    assert has_classification, \
        'Export gate report must contain one of: {}'.format(valid_classifications)
    assert 'sklearn' in content.lower(), \
        'Export gate report must mention sklearn'
    assert 'TFLite' in content or 'tflite' in content.lower(), \
        'Export gate report must address TFLite'


# --- Test 14: V7B report does not claim real ESP32 validation ---
def test_v7b_report_no_esp32_validation_claim():
    content = _read(os.path.join(REPORTS, 'V7B_MODEL_LINEAGE_AUDIT_AND_EXPORT_GATE.md'))
    forbidden = [
        'validado em esp32',
        'benchmark embarcado',
        'latencia medida na placa',
        'ram medida na placa',
        'benchmark real confirmado',
    ]
    for phrase in forbidden:
        assert phrase.lower() not in content.lower(), \
            'V7B report must not claim ESP32 validation: found "{}"'.format(phrase)


# --- Test 15: V7B report does not recommend hardware swap ---
def test_v7b_report_no_hardware_swap():
    content = _read(os.path.join(REPORTS, 'V7B_MODEL_LINEAGE_AUDIT_AND_EXPORT_GATE.md'))
    forbidden = ['esp32-s3', 'raspberry pi', 'trocar a esp32', 'substituir o hardware']
    for phrase in forbidden:
        assert phrase.lower() not in content.lower(), \
            'V7B report must not recommend hardware swap: "{}"'.format(phrase)


# --- Test 16: Model manifest updated with lineage and export status ---
def test_v7b_model_manifest_updated():
    d = _load_json(os.path.join(ARTIFACTS, 'model_manifest.json'))
    assert 'lineage_status' in d, 'model_manifest.json must have lineage_status'
    assert 'export_status' in d, 'model_manifest.json must have export_status'
    assert 'handoff_allowed' in d, 'model_manifest.json must have handoff_allowed'
    assert 'recommended_edge_path' in d, 'model_manifest.json must have recommended_edge_path'
    assert d['handoff_allowed'] is True, 'handoff_allowed must be true (LEGACY_MODEL_WARN accepted)'


# --- Test 17: Lineage audit documents training script as not identified ---
def test_v7b_lineage_audit_documents_training_script_gap():
    rows = _load_csv(os.path.join(OUT, 'v7b_model_lineage_audit.csv'))
    training_row = next((r for r in rows if r['item'] == 'training_script_v1'), None)
    assert training_row is not None, \
        'Lineage audit must have training_script_v1 row'
    status = training_row.get('status', '').upper()
    assert 'LINEAGE_WARN' in status or 'NEEDS_VERIFICATION' in status, \
        'training_script_v1 must be marked LINEAGE_WARN or NEEDS_VERIFICATION, got: {}'.format(status)


# --- Test 18: Feature lineage flags temperature_c as lineage warn ---
def test_v7b_feature_lineage_temperature_warn():
    rows = _load_csv(os.path.join(OUT, 'v7b_feature_lineage_check.csv'))
    temp_row = next((r for r in rows if r['feature_name'] == 'temperature_c'), None)
    assert temp_row is not None, 'Feature lineage must have temperature_c row'
    status = temp_row.get('status', '').upper()
    assert 'WARN' in status or 'CONFIRMED' in status, \
        'temperature_c must be documented (WARN or CONFIRMED), got: {}'.format(status)
    assert temp_row.get('in_model', '').lower() == 'true', \
        'temperature_c must be marked as in_model=true'


# --- Test 19: Golden vectors soc values are in [0, 1] ---
def test_v7b_golden_vectors_soc_in_range():
    rows = _load_csv(os.path.join(ARTIFACTS, 'golden_vectors.csv'))
    for r in rows:
        soc = float(r['soc_sklearn'])
        assert 0.0 <= soc <= 1.0, \
            'Sample {} soc_sklearn={} is outside [0,1]'.format(r['sample_id'], soc)


# --- Test 20: Report mentions baseline tecnico legado language ---
def test_v7b_report_has_legacy_language():
    content = _read(os.path.join(REPORTS, 'V7B_MODEL_LINEAGE_AUDIT_AND_EXPORT_GATE.md'))
    has_legacy = ('baseline tecnico legado' in content.lower() or
                  'legacy_model_warn' in content.lower() or
                  'legado' in content.lower())
    assert has_legacy, \
        'V7B report must mention baseline tecnico legado or LEGACY_MODEL_WARN'


if __name__ == '__main__':
    import sys
    tests = [
        test_v7b_required_files_exist,
        test_v7b_lineage_audit_has_required_items,
        test_v7b_decision_confirms_method_b,
        test_v7b_decision_model_status,
        test_v7b_handoff_allowed_has_conditions,
        test_v7b_feature_lineage_has_6_features,
        test_v7b_feature_lineage_documents_planned,
        test_v7b_golden_vectors_complete,
        test_v7b_golden_vectors_all_pass,
        test_v7b_golden_serial_output_complete,
        test_v7b_model_weights_json_complete,
        test_v7b_c_header_preview_structure,
        test_v7b_export_gate_classification,
        test_v7b_report_no_esp32_validation_claim,
        test_v7b_report_no_hardware_swap,
        test_v7b_model_manifest_updated,
        test_v7b_lineage_audit_documents_training_script_gap,
        test_v7b_feature_lineage_temperature_warn,
        test_v7b_golden_vectors_soc_in_range,
        test_v7b_report_has_legacy_language,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print('[PASS] {}'.format(t.__name__))
            passed += 1
        except Exception as e:
            print('[FAIL] {} -- {}'.format(t.__name__, e))
            failed += 1
    print('')
    print('Results: {}/{} passed'.format(passed, passed + failed))
    sys.exit(0 if failed == 0 else 1)
