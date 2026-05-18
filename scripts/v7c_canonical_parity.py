"""
V7C — Canonical Method B Parity Script.
Validates pure-Python numpy forward pass against sklearn reference for the canonical MLP.
Generates: canonical_golden_vectors.csv, canonical_expected_serial_output.csv,
           v7c_canonical_parity_summary.json.
"""

import csv
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(BASE, 'artifacts', 'edge_v7c')
ART_V7 = os.path.join(BASE, 'artifacts', 'edge_v7')
OUT = os.path.join(BASE, 'outputs', 'v7c_canonical_method_b_artifact')
SAMPLES = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'samples', 'export_validation_inputs.csv')

MISSING = []


def _check(path, label):
    if not os.path.exists(path):
        MISSING.append(label + ': ' + path)
        return False
    return True


_check(os.path.join(ART, 'canonical_model_weights.json'), 'canonical_model_weights.json')
_check(os.path.join(ART, 'canonical_scaler_params.json'), 'canonical_scaler_params.json')
_check(SAMPLES, 'export_validation_inputs.csv')

if MISSING:
    print('[V7C_PARITY] MISSING inputs (run v7c_train_canonical_method_b_model.py first):')
    for m in MISSING:
        print('  ', m)
    raise SystemExit(1)


def _relu(x):
    return x if x > 0.0 else 0.0


def _mlp_forward_numpy(x_scaled, coefs, intercepts):
    """Pure-Python MLP forward pass — ESP32 C proxy."""
    h = list(x_scaled)
    for layer_idx, (W, b) in enumerate(zip(coefs, intercepts)):
        n_out = len(b)
        new_h = []
        for j in range(n_out):
            val = b[j]
            for i, hi in enumerate(h):
                val += hi * W[i][j]
            if layer_idx < len(coefs) - 1:
                val = _relu(val)
            new_h.append(val)
        h = new_h
    return h[0]


def _apply_scaler(raw_features, data_min, scale):
    return [(raw_features[i] - data_min[i]) * scale[i] for i in range(len(raw_features))]


def _load_weights(path):
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    coefs = []
    intercepts = []
    for layer in d['layers']:
        coefs.append(layer['weights'])
        intercepts.append(layer['biases'])
    return coefs, intercepts, d['scaler']


def _anomaly_flags(row, soc_pred):
    """Simplified anomaly detection for golden vectors."""
    flags = []
    v = float(row.get('voltage_v', 0))
    c = float(row.get('current_ma', 0))
    t = float(row.get('temperature_c', 0))
    if v > 4.25 or v < 3.5:
        flags.append('VOLTAGE_OOB')
    if c > 340.0:
        flags.append('CURRENT_SPIKE')
    if t > 45.0 or t < 0.0:
        flags.append('TEMPERATURE_OOB')
    return ','.join(flags) if flags else 'NONE'


def _load_csv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    import pickle
    import numpy as np

    # Load canonical weights
    weights_path = os.path.join(ART, 'canonical_model_weights.json')
    coefs, intercepts, scaler_dict = _load_weights(weights_path)
    data_min = scaler_dict['data_min']
    scale = scaler_dict['scale']
    feature_names = json.load(open(weights_path, encoding='utf-8'))['feature_names']

    # Load sklearn canonical model for reference
    # We use the pkl to get sklearn reference predictions
    # The canonical pkl is not saved separately — use full-dataset retrained model via weights
    # For comparison, load the V1 pkl as reference (sklearn) and numpy proxy matches canonical weights

    # Actually the correct comparison is: canonical_weights numpy vs sklearn canonical model
    # Since we don't save the canonical pkl, we reconstruct sklearn from weights
    # The golden vectors will show numpy(canonical) vs sklearn(V1) for reference comparison,
    # but the canonical parity test is specifically numpy(canonical) vs sklearn(canonical).
    # We load the V1 pkl for the sklearn reference column (historical comparison).

    # Load canonical pkl for sklearn reference (canonical numpy vs canonical sklearn parity)
    PKL_CANONICAL = os.path.join(ART, 'canonical_mlp_pipeline.pkl')
    PKL_V1 = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'model',
                          'iot_method_b_mlp_pipeline.pkl')
    scaler_canonical = None
    model_canonical = None
    scaler_v1 = None
    model_v1 = None
    if os.path.exists(PKL_CANONICAL):
        with open(PKL_CANONICAL, 'rb') as f:
            pipeline_c = pickle.load(f)
        scaler_canonical = pipeline_c['scaler']
        model_canonical = pipeline_c['model']
    if os.path.exists(PKL_V1):
        with open(PKL_V1, 'rb') as f:
            pipeline_v1 = pickle.load(f)
        scaler_v1 = pipeline_v1['scaler']
        model_v1 = pipeline_v1['model']

    # Load validation samples
    rows = _load_csv(SAMPLES)
    feature_cols = feature_names

    golden_rows = []
    serial_rows = []

    all_numpy = []
    all_ref = []

    for i, row in enumerate(rows[:20]):
        try:
            raw = [float(row[col]) for col in feature_cols]
        except (KeyError, ValueError) as e:
            print('[V7C_PARITY] WARNING: sample {} missing feature: {}'.format(i, e))
            raw = [0.0] * len(feature_cols)

        # Canonical numpy forward pass
        x_scaled = _apply_scaler(raw, data_min, scale)
        soc_numpy = max(0.0, min(1.0, _mlp_forward_numpy(x_scaled, coefs, intercepts)))

        # Canonical sklearn reference (primary parity: canonical numpy vs canonical sklearn)
        import numpy as np_lib
        soc_sklearn_canonical = None
        if model_canonical is not None and scaler_canonical is not None:
            X_raw = np_lib.array(raw).reshape(1, -1)
            X_sc = scaler_canonical.transform(X_raw)
            soc_sklearn_canonical = float(np_lib.clip(model_canonical.predict(X_sc)[0], 0.0, 1.0))

        # V1 sklearn reference (historical comparison)
        soc_sklearn_v1 = None
        if model_v1 is not None and scaler_v1 is not None:
            X_raw = np_lib.array(raw).reshape(1, -1)
            X_sc = scaler_v1.transform(X_raw)
            soc_sklearn_v1 = float(np_lib.clip(model_v1.predict(X_sc)[0], 0.0, 1.0))

        # Primary diff: canonical numpy vs canonical sklearn
        abs_diff = abs(soc_numpy - soc_sklearn_canonical) if soc_sklearn_canonical is not None else None
        status = 'CANONICAL_PASS_EXACT' if (abs_diff is not None and abs_diff < 1e-6) else ('CANONICAL_PASS' if (abs_diff is not None and abs_diff < 1e-4) else 'CANONICAL_COMPUTED')

        anomaly = _anomaly_flags(row, soc_numpy)
        has_anomaly = anomaly != 'NONE'

        gold = {
            'sample_id': 'gv_{:02d}'.format(i + 1),
        }
        for j, col in enumerate(feature_cols):
            gold[col] = row.get(col, '0')
        for j, xs in enumerate(x_scaled):
            gold['x_scaled_{}'.format(j)] = '{:.8f}'.format(xs)
        gold['soc_numpy_canonical'] = '{:.8f}'.format(soc_numpy)
        if soc_sklearn_canonical is not None:
            gold['soc_sklearn_canonical'] = '{:.8f}'.format(soc_sklearn_canonical)
            gold['abs_diff_canonical'] = '{:.4e}'.format(abs_diff)
        else:
            gold['soc_sklearn_canonical'] = 'N/A'
            gold['abs_diff_canonical'] = 'N/A'
        if soc_sklearn_v1 is not None:
            gold['soc_sklearn_v1_ref'] = '{:.8f}'.format(soc_sklearn_v1)
        else:
            gold['soc_sklearn_v1_ref'] = 'N/A'
        gold['anomaly_flag'] = '1' if has_anomaly else '0'
        gold['anomaly_reason'] = anomaly
        gold['status'] = status

        golden_rows.append(gold)

        serial = {
            'sample_id': 'gv_{:02d}'.format(i + 1),
            'soc_predicted': '{:.6f}'.format(soc_numpy),
            'anomaly_flag': '1' if has_anomaly else '0',
            'anomaly_score': '1.0' if has_anomaly else '0.0',
            'anomaly_reason': anomaly,
            'anomaly_category': 'PHYSICAL' if has_anomaly else 'NONE',
            'status': status,
        }
        serial_rows.append(serial)
        all_numpy.append(soc_numpy)
        if soc_sklearn_canonical is not None:
            all_ref.append(soc_sklearn_canonical)

    # Write golden vectors
    golden_path = os.path.join(ART, 'canonical_golden_vectors.csv')
    if golden_rows:
        with open(golden_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(golden_rows[0].keys()))
            w.writeheader()
            w.writerows(golden_rows)
    print('[V7C_PARITY] Wrote:', golden_path)

    # Write expected serial output
    serial_path = os.path.join(ART, 'canonical_expected_serial_output.csv')
    if serial_rows:
        with open(serial_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(serial_rows[0].keys()))
            w.writeheader()
            w.writerows(serial_rows)
    print('[V7C_PARITY] Wrote:', serial_path)

    # Compute parity summary
    import numpy as np
    numpy_arr = np.array(all_numpy)
    ref_arr = np.array(all_ref) if all_ref else None

    if ref_arr is not None:
        mae = float(np.mean(np.abs(numpy_arr - ref_arr)))
        rmse = float(np.sqrt(np.mean((numpy_arr - ref_arr) ** 2)))
        max_diff = float(np.max(np.abs(numpy_arr - ref_arr)))
        ss_res = np.sum((ref_arr - numpy_arr) ** 2)
        ss_tot = np.sum((ref_arr - np.mean(ref_arr)) ** 2)
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        verdict = 'PASS_EXACT' if mae < 1e-6 else ('PASS' if mae < 0.001 else 'FAIL_PARITY_MISMATCH')
    else:
        mae = rmse = max_diff = r2 = None
        verdict = 'CANONICAL_PKL_NOT_FOUND'

    summary = {
        'version': 'v7c',
        'date': '2026-05-15',
        'model': 'canonical_mlp_64_32',
        'n_samples': len(all_numpy),
        'parity_description': 'canonical_numpy_proxy vs canonical_sklearn (primary parity check)',
        'numpy_vs_canonical_sklearn': {
            'mae': mae,
            'rmse': rmse,
            'max_diff': max_diff,
            'r2': round(r2, 6) if r2 is not None else None,
        },
        'parity_verdict': verdict,
        'note': 'Primary parity: canonical numpy (C proxy) vs canonical sklearn. Machine-epsilon differences expected (same as V7B). V1 sklearn reference stored separately for historical comparison.',
        'not_yet_validated': [
            'ESP32 hardware latency (gap G09)',
            'ESP32 RAM usage (gap G09)',
            'ESP32 Flash usage (gap G09)',
            'Real sensor parity (Phase 3C)',
            'TFLite conversion (V7C gap — MANUAL_C_INFERENCE_RECOMMENDED)',
        ]
    }
    summary_path = os.path.join(OUT, 'v7c_canonical_parity_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print('[V7C_PARITY] Wrote:', summary_path)
    print('[V7C_PARITY] Verdict:', verdict)
    if mae is not None:
        print('[V7C_PARITY] Canonical numpy vs V1 sklearn: MAE={:.6f}'.format(mae))

    return summary


if __name__ == '__main__':
    result = main()
    print('[V7C_PARITY] Done. Verdict:', result['parity_verdict'])
