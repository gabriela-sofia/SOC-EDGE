"""
Tests for V7 ESP32 Handoff Package.
Verifies package completeness, anomaly injection, script structure, and claim hygiene.
"""

import csv
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(BASE, 'handoff_esp32_v7')
REPORTS = os.path.join(BASE, 'REPORTS')
MODEL_DIR = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'model')
TESTS_DIR = os.path.join(BASE, 'tests')


def _read(path, encoding='utf-8'):
    with open(path, encoding=encoding, errors='replace') as f:
        return f.read()


# --- Test 1: All required handoff files exist ---
def test_v7_required_files_exist():
    required = [
        os.path.join(HANDOFF, 'README_EXECUCAO_ESP32.md'),
        os.path.join(HANDOFF, 'CHECKLIST_RESULTADOS_ESPERADOS.md'),
        os.path.join(HANDOFF, 'RESULT_TEMPLATE_ESP32_RUN.md'),
        os.path.join(HANDOFF, 'serial_replay_input_sample.csv'),
        os.path.join(HANDOFF, 'expected_serial_output_schema.csv'),
        os.path.join(HANDOFF, 'esp32_validation_protocol_v7.md'),
        os.path.join(HANDOFF, 'esp32_soc_replay_validation.py'),
        os.path.join(REPORTS, 'V7_ESP_HANDOFF_AND_EDGE_VALIDATION_PLAN.md'),
    ]
    missing = [p for p in required if not os.path.exists(p)]
    assert not missing, 'Missing V7 files:\n' + '\n'.join(missing)


# --- Test 2: Replay CSV has 50 data rows (excluding header) ---
def test_v7_replay_csv_has_50_samples():
    path = os.path.join(HANDOFF, 'serial_replay_input_sample.csv')
    assert os.path.exists(path), 'serial_replay_input_sample.csv not found'
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 50, 'Expected 50 samples, got {}'.format(len(rows))


# --- Test 3: Replay CSV has 40 normal + 10 anomaly rows ---
def test_v7_replay_csv_anomaly_split():
    path = os.path.join(HANDOFF, 'serial_replay_input_sample.csv')
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    normal = [r for r in rows if r.get('anomaly_injected', '0') == '0']
    anomaly = [r for r in rows if r.get('anomaly_injected', '0') == '1']
    assert len(normal) == 40, 'Expected 40 normal samples, got {}'.format(len(normal))
    assert len(anomaly) == 10, 'Expected 10 anomaly samples, got {}'.format(len(anomaly))


# --- Test 4: Anomaly samples contain critical physical anomaly cases ---
def test_v7_replay_csv_has_critical_anomalies():
    path = os.path.join(HANDOFF, 'serial_replay_input_sample.csv')
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    anomaly_rows = [r for r in rows if r.get('anomaly_injected', '0') == '1']
    voltages = [float(r['voltage_v']) for r in anomaly_rows]
    has_voltage_oor = any(v < 2.5 for v in voltages)
    assert has_voltage_oor, 'No voltage_out_of_range anomaly (v < 2.5) in anomaly samples'
    delta_voltages = [abs(float(r['delta_voltage'])) for r in anomaly_rows]
    has_abrupt_voltage = any(dv > 0.679 for dv in delta_voltages)
    assert has_abrupt_voltage, 'No abrupt_voltage anomaly (|delta_v| > 0.679) in anomaly samples'


# --- Test 5: Validation script has required functions ---
def test_v7_validation_script_has_required_functions():
    path = os.path.join(HANDOFF, 'esp32_soc_replay_validation.py')
    content = _read(path)
    required_functions = [
        'def parse_esp32_log',
        'def parse_reference',
        'def compute_metrics',
        'def verdict',
        'def main',
    ]
    for fn in required_functions:
        assert fn in content, 'Missing function in validation script: {}'.format(fn)


# --- Test 6: Validation script references correct MAE thresholds ---
def test_v7_validation_script_mae_thresholds():
    path = os.path.join(HANDOFF, 'esp32_soc_replay_validation.py')
    content = _read(path)
    assert '0.05' in content, 'PASS threshold 0.05 not found in validation script'
    assert '0.10' in content, 'WARN threshold 0.10 not found in validation script'
    assert 'PASS' in content and 'WARN' in content and 'FAIL' in content, \
        'Validation script must mention PASS, WARN, FAIL'


# --- Test 7: Protocol mentions all three verdicts and MAE criterion ---
def test_v7_protocol_has_pass_warn_fail():
    path = os.path.join(HANDOFF, 'esp32_validation_protocol_v7.md')
    content = _read(path)
    for verdict in ['PASS', 'WARN', 'FAIL']:
        assert verdict in content, 'Protocol missing verdict: {}'.format(verdict)
    assert 'MAE' in content, 'Protocol must mention MAE criterion'
    assert '0.05' in content, 'Protocol must mention MAE threshold 0.05'


# --- Test 8: Result template has all required sections ---
def test_v7_result_template_has_required_sections():
    path = os.path.join(HANDOFF, 'RESULT_TEMPLATE_ESP32_RUN.md')
    content = _read(path)
    required_sections = [
        'Hardware',
        'Latencia',
        'Predicoes',
        'Anomalia',
        'Erros',
        'Declaracao',
    ]
    for section in required_sections:
        assert section in content, 'Result template missing section: {}'.format(section)


# --- Test 9: README specifies ESP32 DevKit V1 and prohibits alternatives ---
def test_v7_readme_hardware_lock():
    path = os.path.join(HANDOFF, 'README_EXECUCAO_ESP32.md')
    content = _read(path)
    assert 'ESP32 DevKit V1' in content, 'README must specify ESP32 DevKit V1'
    prohibited = ['ESP32-S3', 'Raspberry Pi', 'STM32', 'Arduino UNO']
    for hw in prohibited:
        assert hw in content, 'README must explicitly prohibit: {}'.format(hw)


# --- Test 10: Hardware metrics (RAM/Flash/latency) presented as to-be-measured ---
def test_v7_hardware_metrics_are_not_overclaimed():
    plan_path = os.path.join(REPORTS, 'V7_ESP_HANDOFF_AND_EDGE_VALIDATION_PLAN.md')
    protocol_path = os.path.join(HANDOFF, 'esp32_validation_protocol_v7.md')
    plan_content = _read(plan_path)
    protocol_content = _read(protocol_path)
    combined = plan_content + protocol_content
    forbidden_claims = [
        'RAM confirmada',
        'Flash confirmada',
        'latencia confirmada',
        'medimos RAM',
        'medimos Flash',
    ]
    for claim in forbidden_claims:
        assert claim.lower() not in combined.lower(), \
            'V7 must not claim measured hardware metrics before ESP32 run: "{}"'.format(claim)
    measure_markers = ['a ser medido', 'nao medido', 'medir com', 'opcional', 'informativo']
    has_marker = any(m in combined.lower() for m in measure_markers)
    assert has_marker, 'V7 docs must indicate that hardware metrics are to be measured'


# --- Test 11: Scaler params JSON exists with correct 6 features ---
def test_v7_scaler_params_exist_and_complete():
    path = os.path.join(MODEL_DIR, 'scaler_params.json')
    assert os.path.exists(path), 'scaler_params.json not found in model dir'
    with open(path, encoding='utf-8') as f:
        params = json.load(f)
    required_keys = ['data_min', 'data_max', 'scale']
    for key in required_keys:
        assert key in params, 'scaler_params.json missing key: {}'.format(key)
    assert len(params['data_min']) == 6, \
        'scaler_params.json data_min must have 6 values, got {}'.format(len(params['data_min']))


# --- Test 12: Expected output schema has required columns ---
def test_v7_output_schema_has_required_columns():
    path = os.path.join(HANDOFF, 'expected_serial_output_schema.csv')
    assert os.path.exists(path), 'expected_serial_output_schema.csv not found'
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    column_names = [r['column_name'] for r in rows]
    assert 'sample_id' in column_names, 'Output schema missing sample_id'
    assert 'soc_predicted' in column_names, 'Output schema missing soc_predicted'


# --- Test 13: V7 report mentions it comes after V6.1 ---
def test_v7_report_references_v61():
    path = os.path.join(REPORTS, 'V7_ESP_HANDOFF_AND_EDGE_VALIDATION_PLAN.md')
    content = _read(path)
    assert 'V6.1' in content, 'V7 report must reference V6.1 as predecessor'
    assert 'READY_FOR_COMMIT' in content or 'auditoria' in content.lower(), \
        'V7 report must reference V6.1 audit status'


# --- Test 14: Replay CSV columns match feature order ---
def test_v7_replay_csv_columns_match_feature_order():
    csv_path = os.path.join(HANDOFF, 'serial_replay_input_sample.csv')
    feature_path = os.path.join(MODEL_DIR, 'feature_order.json')
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        csv_fields = reader.fieldnames or []
    with open(feature_path, encoding='utf-8') as f:
        feature_order = json.load(f)
    raw_features = feature_order if isinstance(feature_order, list) else feature_order.get('features', [])
    features = [f['name'] if isinstance(f, dict) else f for f in raw_features]
    for feat in features:
        assert feat in csv_fields, 'Feature {} missing from replay CSV columns'.format(feat)


if __name__ == '__main__':
    import sys
    tests = [
        test_v7_required_files_exist,
        test_v7_replay_csv_has_50_samples,
        test_v7_replay_csv_anomaly_split,
        test_v7_replay_csv_has_critical_anomalies,
        test_v7_validation_script_has_required_functions,
        test_v7_validation_script_mae_thresholds,
        test_v7_protocol_has_pass_warn_fail,
        test_v7_result_template_has_required_sections,
        test_v7_readme_hardware_lock,
        test_v7_hardware_metrics_are_not_overclaimed,
        test_v7_scaler_params_exist_and_complete,
        test_v7_output_schema_has_required_columns,
        test_v7_report_references_v61,
        test_v7_replay_csv_columns_match_feature_order,
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
