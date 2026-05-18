"""
Tests for V7A Edge-Ready Offline Artifact Freeze and Parity Simulation.
Verifies schema, artifacts, outputs, claim hygiene, and simulation correctness.
"""

import csv
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS = os.path.join(BASE, 'artifacts', 'edge_v7')
OUT = os.path.join(BASE, 'outputs', 'v7_edge_ready_offline')
SCRIPTS = os.path.join(BASE, 'scripts')
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


# --- Test 1: All V7A artifacts exist ---
def test_v7a_required_artifacts_exist():
    required = [
        os.path.join(ARTIFACTS, 'feature_order.json'),
        os.path.join(ARTIFACTS, 'input_schema.csv'),
        os.path.join(ARTIFACTS, 'scaler_params.json'),
        os.path.join(ARTIFACTS, 'model_manifest.json'),
        os.path.join(OUT, 'v7_input_inventory.csv'),
        os.path.join(OUT, 'v7_offline_parity_summary.json'),
        os.path.join(OUT, 'v7_offline_parity_table.csv'),
        os.path.join(OUT, 'v7_missing_inputs.csv'),
        os.path.join(OUT, 'v7_serial_like_output.csv'),
        os.path.join(OUT, 'v7_fault_injection_results.csv'),
        os.path.join(OUT, 'v7_anomaly_calibration_table.csv'),
        os.path.join(SCRIPTS, 'v7_edge_ready_offline_parity.py'),
        os.path.join(SCRIPTS, 'v7_edge_runtime_simulator.py'),
        os.path.join(SCRIPTS, 'v7_fault_injection_offline.py'),
        os.path.join(REPORTS, 'V7_EDGE_READY_OFFLINE_VALIDATION_REPORT.md'),
    ]
    missing = [p for p in required if not os.path.exists(p)]
    assert not missing, 'Missing V7A artifacts:\n' + '\n'.join(missing)


# --- Test 2: Feature order has exactly 6 features ---
def test_v7a_feature_order_has_6_features():
    d = _load_json(os.path.join(ARTIFACTS, 'feature_order.json'))
    features = d.get('features', [])
    assert len(features) == 6, 'Expected 6 features, got {}'.format(len(features))
    names = [f['name'] if isinstance(f, dict) else f for f in features]
    expected = ['voltage_v', 'temperature_c', 'current_ma',
                'delta_voltage', 'delta_temperature', 'delta_current']
    assert names == expected, 'Feature order mismatch: {} vs {}'.format(names, expected)


# --- Test 3: Scaler has correct structure and 6 values ---
def test_v7a_scaler_params_complete():
    d = _load_json(os.path.join(ARTIFACTS, 'scaler_params.json'))
    for key in ['data_min', 'data_max', 'scale']:
        assert key in d, 'Missing key in scaler_params.json: {}'.format(key)
        assert len(d[key]) == 6, 'Key {} must have 6 values'.format(key)
    assert 'FROZEN' in d.get('status', ''), 'scaler_params.json must be marked FROZEN'


# --- Test 4: Model manifest is complete ---
def test_v7a_model_manifest_complete():
    d = _load_json(os.path.join(ARTIFACTS, 'model_manifest.json'))
    required_keys = ['model_type', 'architecture', 'parameter_count',
                     'source_weights_json', 'deployment_restrictions']
    for key in required_keys:
        assert key in d, 'model_manifest.json missing key: {}'.format(key)
    arch = d['architecture']
    assert arch['input_size'] == 6, 'Architecture must have input_size=6'
    # status may be EDGE_CANDIDATE or LEGACY_MODEL_WARN (updated in V7B)
    status = d.get('status', '')
    assert 'EDGE_CANDIDATE' in status or 'LEGACY_MODEL' in status, \
        'Manifest must be marked EDGE_CANDIDATE or LEGACY_MODEL_WARN, got: {}'.format(status)


# --- Test 5: Model manifest marks TFLite as NOT_DONE ---
def test_v7a_model_manifest_tflite_not_done():
    d = _load_json(os.path.join(ARTIFACTS, 'model_manifest.json'))
    # tflite status may be in embedding_status (V7A) or export_details (V7B)
    embed = d.get('embedding_status', {})
    export_d = d.get('export_details', {})
    tflite = embed.get('tflite_conversion', '') or export_d.get('tflite_conversion', '')
    assert 'NOT_DONE' in tflite or 'BLOCKED' in tflite or 'BLOCKED' in d.get('export_status', ''), \
        'model_manifest must mark TFLite as NOT_DONE or BLOCKED, got: {}'.format(tflite)


# --- Test 6: Parity summary has PASS_EXACT or PASS verdict ---
def test_v7a_parity_verdict_is_pass():
    d = _load_json(os.path.join(OUT, 'v7_offline_parity_summary.json'))
    verdict = d.get('parity_verdict', '')
    assert 'PASS' in verdict, \
        'Parity verdict must be PASS*, got: {}'.format(verdict)


# --- Test 7: Parity summary documents what is NOT validated ---
def test_v7a_parity_summary_documents_pending():
    d = _load_json(os.path.join(OUT, 'v7_offline_parity_summary.json'))
    pending = d.get('not_yet_validated', [])
    assert len(pending) >= 3, 'Parity summary must list at least 3 pending items'
    combined = ' '.join(pending).lower()
    assert 'esp32' in combined or 'hardware' in combined or 'latency' in combined, \
        'Pending items must mention ESP32, hardware, or latency'


# --- Test 8: Parity table has sample rows with soc_numpy ---
def test_v7a_parity_table_has_data():
    rows = _load_csv(os.path.join(OUT, 'v7_offline_parity_table.csv'))
    assert len(rows) > 0, 'Parity table is empty'
    assert 'soc_numpy' in rows[0], 'Parity table must have soc_numpy column'
    assert 'soc_ref' in rows[0], 'Parity table must have soc_ref column'
    for r in rows:
        assert r.get('status') == 'OK', \
            'Sample {} has non-OK status: {}'.format(r.get('sample_id'), r.get('status'))


# --- Test 9: Serial-like output has required columns and 50 rows ---
def test_v7a_serial_output_complete():
    rows = _load_csv(os.path.join(OUT, 'v7_serial_like_output.csv'))
    assert len(rows) == 50, 'Expected 50 rows in serial output, got {}'.format(len(rows))
    required_cols = ['timestamp', 'voltage_v', 'current_ma', 'temperature_c',
                     'soc_predicted', 'anomaly_flag', 'anomaly_reason', 'status']
    if rows:
        for col in required_cols:
            assert col in rows[0], 'Serial output missing column: {}'.format(col)


# --- Test 10: Serial output does not use MISSING_MODEL ---
def test_v7a_serial_output_has_soc_predictions():
    rows = _load_csv(os.path.join(OUT, 'v7_serial_like_output.csv'))
    missing_model = [r for r in rows if r.get('soc_predicted') == 'MISSING_MODEL']
    assert not missing_model, \
        '{} rows have MISSING_MODEL — mlp_weights.json must be available'.format(len(missing_model))


# --- Test 11: Fault injection ran 8 scenarios ---
def test_v7a_fault_injection_has_8_scenarios():
    rows = _load_csv(os.path.join(OUT, 'v7_fault_injection_results.csv'))
    assert len(rows) == 8, 'Expected 8 fault injection scenarios, got {}'.format(len(rows))
    scenarios = {r['scenario'] for r in rows}
    expected = {'voltage_spike', 'current_spike', 'temperature_jump', 'voltage_flatline',
                'current_dropout', 'noise_burst', 'soc_temporal_incoherence',
                'domain_shift_current_scale'}
    assert scenarios == expected, \
        'Fault injection missing scenarios: {}'.format(expected - scenarios)


# --- Test 12: Physical anomaly scenarios (voltage, current, temp) detected at 100% ---
def test_v7a_physical_anomalies_detected():
    rows = _load_csv(os.path.join(OUT, 'v7_fault_injection_results.csv'))
    physical = {r['scenario']: float(r['flag_rate']) for r in rows
                if r['scenario'] in ('voltage_spike', 'current_spike', 'temperature_jump')}
    for name, rate in physical.items():
        assert rate == 1.0, \
            'Physical anomaly {} should have flag_rate=1.0, got {}'.format(name, rate)


# --- Test 13: Anomaly calibration table has required columns ---
def test_v7a_anomaly_calibration_table_columns():
    rows = _load_csv(os.path.join(OUT, 'v7_anomaly_calibration_table.csv'))
    assert len(rows) > 0, 'Anomaly calibration table is empty'
    required = ['rule_name', 'threshold_origin', 'requires_esp_validation',
                'expected_runtime_cost', 'status']
    for col in required:
        assert col in rows[0], 'Calibration table missing column: {}'.format(col)


# --- Test 14: No calibration threshold is marked as "final" ---
def test_v7a_no_threshold_marked_final():
    rows = _load_csv(os.path.join(OUT, 'v7_anomaly_calibration_table.csv'))
    for r in rows:
        status = r.get('status', '').upper()
        assert 'FINAL' not in status, \
            'Rule {} is marked FINAL — must be FROZEN_CANDIDATE or PLANNED until ESP32 validated'.format(
                r.get('rule_name'))


# --- Test 15: Report mentions pre-embarque language ---
def test_v7a_report_has_required_language():
    content = _read(os.path.join(REPORTS, 'V7_EDGE_READY_OFFLINE_VALIDATION_REPORT.md'))
    required_phrases = [
        'pre-embarque',
        'simulacao offline de runtime',
        'pendente de benchmark real na ESP32',
        'latencia',
    ]
    for phrase in required_phrases:
        assert phrase.lower() in content.lower(), \
            'Report missing required language: "{}"'.format(phrase)


# --- Test 16: Report does not claim ESP32 benchmark ---
def test_v7a_report_no_esp32_benchmark_claim():
    content = _read(os.path.join(REPORTS, 'V7_EDGE_READY_OFFLINE_VALIDATION_REPORT.md'))
    forbidden = [
        'latencia medida na esp32',
        'ram medida',
        'flash medida',
        'benchmarkado na placa',
        'benchmark real confirmado',
    ]
    for phrase in forbidden:
        assert phrase.lower() not in content.lower(), \
            'Report must not claim ESP32 benchmark: found "{}"'.format(phrase)


# --- Test 17: Report does not recommend switching ESP32 ---
def test_v7a_report_no_hardware_swap():
    content = _read(os.path.join(REPORTS, 'V7_EDGE_READY_OFFLINE_VALIDATION_REPORT.md'))
    forbidden = ['esp32-s3', 'raspberry pi', 'trocar a placa', 'substituir o hardware']
    for phrase in forbidden:
        assert phrase.lower() not in content.lower(), \
            'Report must not recommend hardware swap: found "{}"'.format(phrase)


# --- Test 18: Input inventory documents missing items (TFLite, real sensor) ---
def test_v7a_inventory_documents_missing():
    rows = _load_csv(os.path.join(OUT, 'v7_input_inventory.csv'))
    missing = [r for r in rows if r.get('exists', 'true').lower() == 'false']
    assert len(missing) >= 2, \
        'Inventory must document at least 2 missing items (TFLite, real sensor data)'
    missing_items = [r['item'] for r in missing]
    has_tflite = any('tflite' in item.lower() or 'tfl' in item.lower() for item in missing_items)
    assert has_tflite, 'Inventory must document missing TFLite model'


# --- Test 19: Edge simulator script has no pandas import in main loop ---
def test_v7a_simulator_no_pandas_main_loop():
    content = _read(os.path.join(SCRIPTS, 'v7_edge_runtime_simulator.py'))
    # Check that pandas is not imported at all (the constraint is "no pandas in main loop")
    # We verify the script does not import pandas
    assert 'import pandas' not in content, \
        'Edge runtime simulator must not import pandas (ESP32 proxy — pandas not available on embedded)'


# --- Test 20: Parity script has fallback if sklearn not available ---
def test_v7a_parity_script_has_fallback():
    content = _read(os.path.join(SCRIPTS, 'v7_edge_ready_offline_parity.py'))
    assert 'missing.append' in content or 'MISSING' in content, \
        'Parity script must handle missing inputs gracefully'
    assert 'not os.path.exists' in content, \
        'Parity script must check file existence before loading'


if __name__ == '__main__':
    import sys
    tests = [
        test_v7a_required_artifacts_exist,
        test_v7a_feature_order_has_6_features,
        test_v7a_scaler_params_complete,
        test_v7a_model_manifest_complete,
        test_v7a_model_manifest_tflite_not_done,
        test_v7a_parity_verdict_is_pass,
        test_v7a_parity_summary_documents_pending,
        test_v7a_parity_table_has_data,
        test_v7a_serial_output_complete,
        test_v7a_serial_output_has_soc_predictions,
        test_v7a_fault_injection_has_8_scenarios,
        test_v7a_physical_anomalies_detected,
        test_v7a_anomaly_calibration_table_columns,
        test_v7a_no_threshold_marked_final,
        test_v7a_report_has_required_language,
        test_v7a_report_no_esp32_benchmark_claim,
        test_v7a_report_no_hardware_swap,
        test_v7a_inventory_documents_missing,
        test_v7a_simulator_no_pandas_main_loop,
        test_v7a_parity_script_has_fallback,
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
