"""
Tests for V7C Canonical Method B Artifact Mastering.
Verifies schema, training artifacts, parity, anomaly protocol, reports, and handoff package.
"""

import csv
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'outputs', 'v7c_canonical_method_b_artifact')
ART = os.path.join(BASE, 'artifacts', 'edge_v7c')
SCRIPTS = os.path.join(BASE, 'scripts')
REPORTS = os.path.join(BASE, 'REPORTS')
HANDOFF = os.path.join(BASE, 'handoff_esp32_v7c')


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _load_csv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


# --- Test 1: All V7C required files exist ---
def test_v7c_required_files_exist():
    required = [
        os.path.join(OUT, 'v7c_scientific_inventory.csv'),
        os.path.join(OUT, 'v7c_feature_unit_reconciliation.csv'),
        os.path.join(ART, 'canonical_feature_order.json'),
        os.path.join(ART, 'canonical_scaler_params.json'),
        os.path.join(ART, 'canonical_model_weights.json'),
        os.path.join(ART, 'canonical_model_weights_preview.h'),
        os.path.join(ART, 'canonical_golden_vectors.csv'),
        os.path.join(ART, 'canonical_expected_serial_output.csv'),
        os.path.join(OUT, 'v7c_model_benchmark.csv'),
        os.path.join(OUT, 'v7c_split_validation_results.csv'),
        os.path.join(OUT, 'v7c_feature_ablation.csv'),
        os.path.join(OUT, 'v7c_training_summary.json'),
        os.path.join(OUT, 'v7c_canonical_parity_summary.json'),
        os.path.join(OUT, 'v7c_anomaly_protocol.csv'),
        os.path.join(OUT, 'v7c_fault_injection_matrix.csv'),
        os.path.join(OUT, 'v7c_anomaly_calibration_summary.json'),
        os.path.join(OUT, 'v7c_domain_shift_summary.md'),
        os.path.join(OUT, 'v7c_soh_bridge_plan.md'),
        os.path.join(OUT, 'v7c_scientific_source_to_design_map.csv'),
        os.path.join(REPORTS, 'V7C_CANONICAL_METHOD_B_ARTIFACT_MASTERING.md'),
        os.path.join(SCRIPTS, 'v7c_train_canonical_method_b_model.py'),
        os.path.join(SCRIPTS, 'v7c_canonical_parity.py'),
        os.path.join(SCRIPTS, 'v7c_anomaly_protocol_calibration.py'),
        os.path.join(HANDOFF, 'IMPLEMENTATION_GUIDE_V7C.md'),
        os.path.join(HANDOFF, 'LIMITATIONS_V7C.md'),
        os.path.join(HANDOFF, 'FILE_MANIFEST_V7C.csv'),
        os.path.join(HANDOFF, 'model', 'canonical_model_weights.json'),
        os.path.join(HANDOFF, 'validation', 'canonical_golden_vectors.csv'),
    ]
    missing = [p for p in required if not os.path.exists(p)]
    assert not missing, 'Missing V7C files:\n' + '\n'.join(missing)


# --- Test 2: Canonical feature order has 6 features in correct order ---
def test_v7c_canonical_feature_order():
    d = _load_json(os.path.join(ART, 'canonical_feature_order.json'))
    assert d.get('version') == 'v7c', 'canonical_feature_order.json must be version v7c'
    features = d.get('features', [])
    assert len(features) == 6, 'Expected 6 features, got {}'.format(len(features))
    expected = ['voltage_v', 'temperature_c', 'current_ma',
                'delta_voltage', 'delta_temperature', 'delta_current']
    names = [f['name'] for f in features]
    assert names == expected, 'Feature order mismatch: {}'.format(names)
    # temperature_c must document canonical decision to keep it
    temp_feat = next(f for f in features if f['name'] == 'temperature_c')
    assert 'CANONICAL' in temp_feat.get('reconciliation_status', '').upper(), \
        'temperature_c must document canonical decision in reconciliation_status'


# --- Test 3: Canonical scaler has 6 values and v7c version ---
def test_v7c_canonical_scaler_complete():
    d = _load_json(os.path.join(ART, 'canonical_scaler_params.json'))
    assert d.get('version') == 'v7c', 'canonical_scaler_params must be version v7c'
    for key in ['data_min', 'data_max', 'scale']:
        assert key in d, 'Missing key: {}'.format(key)
        assert len(d[key]) == 6, 'Key {} must have 6 values'.format(key)
    assert 'CANONICAL' in d.get('status', ''), 'scaler must have CANONICAL status'


# --- Test 4: Benchmark has all three models ---
def test_v7c_benchmark_has_three_models():
    rows = _load_csv(os.path.join(OUT, 'v7c_model_benchmark.csv'))
    models = {r['model'] for r in rows}
    assert 'Ridge' in models, 'Benchmark must include Ridge'
    assert any('MLP' in m and ('small' in m or '32' in m) for m in models), \
        'Benchmark must include MLP-small'
    assert any('canonical' in m.lower() or ('64' in m and '32' in m) for m in models), \
        'Benchmark must include MLP-canonical'


# --- Test 5: Canonical MLP achieves R² >= 0.75 ---
def test_v7c_canonical_mlp_r2_threshold():
    rows = _load_csv(os.path.join(OUT, 'v7c_model_benchmark.csv'))
    canonical_row = next((r for r in rows if 'canonical' in r['model'].lower()), None)
    assert canonical_row is not None, 'No canonical MLP row in benchmark'
    r2 = float(canonical_row['R2_LONO'])
    assert r2 >= 0.75, \
        'Canonical MLP R2_LONO={} must be >= 0.75'.format(r2)


# --- Test 6: Training summary has correct verdict ---
def test_v7c_training_summary_verdict():
    d = _load_json(os.path.join(OUT, 'v7c_training_summary.json'))
    valid_verdicts = {
        'CANONICAL_MODEL_APPROVED_FOR_ESP_HANDOFF',
        'LEGACY_MODEL_ONLY_FOR_TECHNICAL_HANDOFF',
        'CANONICAL_MODEL_NEEDS_FIX',
        'MODEL_TRAINING_BLOCKED',
    }
    verdict = d.get('verdict', '')
    assert verdict in valid_verdicts, \
        'Training summary verdict must be one of {}, got: {}'.format(valid_verdicts, verdict)


# --- Test 7: Feature ablation has 9 rows including all_6 baseline ---
def test_v7c_feature_ablation_complete():
    rows = _load_csv(os.path.join(OUT, 'v7c_feature_ablation.csv'))
    assert len(rows) == 9, 'Expected 9 ablation rows, got {}'.format(len(rows))
    subsets = {r['subset_name'] for r in rows}
    assert 'all_6' in subsets, 'Ablation must include all_6 baseline'
    assert 'drop_temperature_c' in subsets, 'Ablation must include drop_temperature_c'


# --- Test 8: Ablation shows temperature_c contributes positively ---
def test_v7c_ablation_temperature_contribution():
    rows = _load_csv(os.path.join(OUT, 'v7c_feature_ablation.csv'))
    baseline = next(r for r in rows if r['subset_name'] == 'all_6')
    no_temp = next((r for r in rows if r['subset_name'] == 'drop_temperature_c'), None)
    assert no_temp is not None, 'Ablation must have drop_temperature_c row'
    r2_baseline = float(baseline['R2_LONO'])
    r2_no_temp = float(no_temp['R2_LONO'])
    assert r2_baseline > r2_no_temp, \
        'Including temperature_c must improve R2: baseline={} no_temp={}'.format(
            r2_baseline, r2_no_temp)


# --- Test 9: Canonical parity is PASS_EXACT ---
def test_v7c_canonical_parity_pass_exact():
    d = _load_json(os.path.join(OUT, 'v7c_canonical_parity_summary.json'))
    verdict = d.get('parity_verdict', '')
    assert verdict == 'PASS_EXACT', \
        'Canonical parity must be PASS_EXACT, got: {}'.format(verdict)
    mae = d.get('numpy_vs_canonical_sklearn', {}).get('mae', 1.0)
    assert mae is not None and float(mae) < 1e-5, \
        'Canonical parity MAE must be < 1e-5, got: {}'.format(mae)


# --- Test 10: Parity summary documents pending items ---
def test_v7c_parity_summary_documents_pending():
    d = _load_json(os.path.join(OUT, 'v7c_canonical_parity_summary.json'))
    pending = d.get('not_yet_validated', [])
    assert len(pending) >= 3, 'Parity summary must list at least 3 pending items'
    combined = ' '.join(pending).lower()
    assert 'esp32' in combined or 'hardware' in combined or 'latency' in combined, \
        'Pending items must mention ESP32, hardware, or latency'


# --- Test 11: Canonical golden vectors have 20 rows and correct status ---
def test_v7c_canonical_golden_vectors_complete():
    rows = _load_csv(os.path.join(ART, 'canonical_golden_vectors.csv'))
    assert len(rows) == 20, 'Expected 20 canonical golden vectors, got {}'.format(len(rows))
    required_cols = ['sample_id', 'soc_numpy_canonical', 'status']
    if rows:
        for col in required_cols:
            assert col in rows[0], 'Golden vectors missing column: {}'.format(col)


# --- Test 12: All golden vectors have CANONICAL_PASS or CANONICAL_PASS_EXACT status ---
def test_v7c_golden_vectors_pass_status():
    rows = _load_csv(os.path.join(ART, 'canonical_golden_vectors.csv'))
    failures = [r for r in rows if 'CANONICAL_PASS' not in r.get('status', '').upper()]
    assert not failures, \
        '{} golden vectors do not have CANONICAL_PASS status: {}'.format(
            len(failures), [r['sample_id'] for r in failures])


# --- Test 13: Anomaly protocol has 9 rules all FROZEN_CANDIDATE ---
def test_v7c_anomaly_protocol_has_9_rules():
    rows = _load_csv(os.path.join(OUT, 'v7c_anomaly_protocol.csv'))
    assert len(rows) == 9, 'Expected 9 anomaly rules, got {}'.format(len(rows))
    for r in rows:
        status = r.get('status', '').upper()
        assert 'FROZEN_CANDIDATE' in status, \
            'Rule {} must be FROZEN_CANDIDATE, got: {}'.format(r.get('rule_id'), status)


# --- Test 14: Anomaly protocol includes thermal_composite (new V7C rule) ---
def test_v7c_anomaly_includes_thermal_composite():
    rows = _load_csv(os.path.join(OUT, 'v7c_anomaly_protocol.csv'))
    names = {r['rule_name'] for r in rows}
    assert 'thermal_composite' in names, \
        'V7C anomaly protocol must include thermal_composite rule'


# --- Test 15: Fault injection matrix has 9 scenarios ---
def test_v7c_fault_injection_has_9_scenarios():
    rows = _load_csv(os.path.join(OUT, 'v7c_fault_injection_matrix.csv'))
    assert len(rows) == 9, 'Expected 9 fault injection scenarios, got {}'.format(len(rows))
    scenarios = {r['scenario'] for r in rows}
    expected = {'voltage_spike', 'current_spike', 'temperature_jump', 'voltage_flatline',
                'current_dropout', 'noise_burst', 'soc_temporal_incoherence',
                'domain_shift_current_scale', 'thermal_composite'}
    assert scenarios == expected, \
        'Fault injection missing scenarios: {}'.format(expected - scenarios)


# --- Test 16: Feature reconciliation documents all 6 features ---
def test_v7c_feature_reconciliation_covers_all():
    rows = _load_csv(os.path.join(OUT, 'v7c_feature_unit_reconciliation.csv'))
    features = {r['feature_name'] for r in rows}
    expected = {'voltage_v', 'temperature_c', 'current_ma',
                'delta_voltage', 'delta_temperature', 'delta_current'}
    assert features == expected, \
        'Feature reconciliation must cover exactly 6 features, got: {}'.format(features)


# --- Test 17: Reconciliation documents temperature_c canonical decision ---
def test_v7c_reconciliation_temperature_canonical_keep():
    rows = _load_csv(os.path.join(OUT, 'v7c_feature_unit_reconciliation.csv'))
    temp_row = next((r for r in rows if r['feature_name'] == 'temperature_c'), None)
    assert temp_row is not None, 'Reconciliation must have temperature_c row'
    decision = temp_row.get('canonical_decision', '').upper()
    assert 'KEEP' in decision, \
        'temperature_c canonical_decision must say KEEP, got: {}'.format(decision)


# --- Test 18: Canonical model weights has correct structure ---
def test_v7c_canonical_model_weights_structure():
    d = _load_json(os.path.join(ART, 'canonical_model_weights.json'))
    assert d.get('version') == 'v7c', 'canonical_model_weights must be version v7c'
    assert 'layers' in d, 'canonical_model_weights must have layers'
    assert len(d['layers']) == 3, 'Expected 3 layers'
    total = d.get('total_parameters', 0)
    assert total == 2561, 'Total parameters must be 2561, got {}'.format(total)
    for layer in d['layers']:
        assert 'weights' in layer and 'biases' in layer, \
            'Layer {} missing weights or biases'.format(layer.get('layer_index'))


# --- Test 19: Report has CANONICAL_MODEL_APPROVED language ---
def test_v7c_report_has_approved_language():
    content = _read(os.path.join(REPORTS, 'V7C_CANONICAL_METHOD_B_ARTIFACT_MASTERING.md'))
    assert 'CANONICAL_MODEL_APPROVED_FOR_ESP_HANDOFF' in content, \
        'V7C report must mention the verdict CANONICAL_MODEL_APPROVED_FOR_ESP_HANDOFF'


# --- Test 20: Report does not claim ESP32 benchmark ---
def test_v7c_report_no_esp32_benchmark_claim():
    content = _read(os.path.join(REPORTS, 'V7C_CANONICAL_METHOD_B_ARTIFACT_MASTERING.md'))
    forbidden = [
        'latencia medida na esp32',
        'ram medida',
        'flash medida',
        'benchmarkado na placa',
        'benchmark real confirmado',
    ]
    for phrase in forbidden:
        assert phrase.lower() not in content.lower(), \
            'V7C report must not claim ESP32 benchmark: found "{}"'.format(phrase)


# --- Test 21: Report does not recommend hardware swap ---
def test_v7c_report_no_hardware_swap():
    content = _read(os.path.join(REPORTS, 'V7C_CANONICAL_METHOD_B_ARTIFACT_MASTERING.md'))
    forbidden = ['esp32-s3', 'raspberry pi', 'trocar a placa', 'substituir o hardware']
    for phrase in forbidden:
        assert phrase.lower() not in content.lower(), \
            'V7C report must not recommend hardware swap: "{}"'.format(phrase)


# --- Test 22: Handoff package has required files ---
def test_v7c_handoff_package_complete():
    required = [
        os.path.join(HANDOFF, 'model', 'canonical_model_weights.json'),
        os.path.join(HANDOFF, 'model', 'canonical_model_weights_preview.h'),
        os.path.join(HANDOFF, 'model', 'canonical_scaler_params.json'),
        os.path.join(HANDOFF, 'model', 'canonical_feature_order.json'),
        os.path.join(HANDOFF, 'validation', 'canonical_golden_vectors.csv'),
        os.path.join(HANDOFF, 'validation', 'canonical_expected_serial_output.csv'),
        os.path.join(HANDOFF, 'IMPLEMENTATION_GUIDE_V7C.md'),
        os.path.join(HANDOFF, 'LIMITATIONS_V7C.md'),
        os.path.join(HANDOFF, 'FILE_MANIFEST_V7C.csv'),
    ]
    missing = [p for p in required if not os.path.exists(p)]
    assert not missing, 'Handoff package missing files:\n' + '\n'.join(missing)


# --- Test 23: Implementation guide mentions mA (not A) ---
def test_v7c_implementation_guide_mentions_ma():
    content = _read(os.path.join(HANDOFF, 'IMPLEMENTATION_GUIDE_V7C.md'))
    assert 'mA' in content or 'milliamp' in content.lower() or 'MILIAMPERES' in content, \
        'Implementation guide must mention mA unit'
    assert 'current_ma' in content, \
        'Implementation guide must mention current_ma feature'


# --- Test 24: Scientific source-to-design map has required decisions ---
def test_v7c_source_to_design_map_complete():
    rows = _load_csv(os.path.join(OUT, 'v7c_scientific_source_to_design_map.csv'))
    decisions = {r['design_decision'] for r in rows}
    assert len(rows) >= 8, 'Source-to-design map must have at least 8 entries'
    has_method_b = any('method_b' in d.lower() or 'soc_method_b' in d.lower() or 'Method B' in d for d in decisions)
    assert has_method_b, 'Source-to-design map must document Method B target decision'


# --- Test 25: Canonical parity script has file existence check ---
def test_v7c_parity_script_has_file_check():
    content = _read(os.path.join(SCRIPTS, 'v7c_canonical_parity.py'))
    assert 'not os.path.exists' in content or 'MISSING' in content, \
        'Parity script must check file existence before loading'


if __name__ == '__main__':
    import sys
    tests = [
        test_v7c_required_files_exist,
        test_v7c_canonical_feature_order,
        test_v7c_canonical_scaler_complete,
        test_v7c_benchmark_has_three_models,
        test_v7c_canonical_mlp_r2_threshold,
        test_v7c_training_summary_verdict,
        test_v7c_feature_ablation_complete,
        test_v7c_ablation_temperature_contribution,
        test_v7c_canonical_parity_pass_exact,
        test_v7c_parity_summary_documents_pending,
        test_v7c_canonical_golden_vectors_complete,
        test_v7c_golden_vectors_pass_status,
        test_v7c_anomaly_protocol_has_9_rules,
        test_v7c_anomaly_includes_thermal_composite,
        test_v7c_fault_injection_has_9_scenarios,
        test_v7c_feature_reconciliation_covers_all,
        test_v7c_reconciliation_temperature_canonical_keep,
        test_v7c_canonical_model_weights_structure,
        test_v7c_report_has_approved_language,
        test_v7c_report_no_esp32_benchmark_claim,
        test_v7c_report_no_hardware_swap,
        test_v7c_handoff_package_complete,
        test_v7c_implementation_guide_mentions_ma,
        test_v7c_source_to_design_map_complete,
        test_v7c_parity_script_has_file_check,
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
