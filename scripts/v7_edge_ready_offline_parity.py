"""
v7_edge_ready_offline_parity.py
V7A — Offline parity validation: pure-numpy inference vs sklearn reference.

Validates that the pure-numpy ESP32-equivalent inference path (using JSON weights)
produces the same SOC predictions as the sklearn pipeline (pkl).
This is the offline proxy for ESP32 parity BEFORE the physical board is available.

Does NOT claim:
- ESP32 benchmark (latency/RAM/Flash not measured)
- Real sensor validation
- Production readiness

Outputs:
  outputs/v7_edge_ready_offline/v7_offline_parity_summary.json
  outputs/v7_edge_ready_offline/v7_offline_parity_table.csv
  outputs/v7_edge_ready_offline/v7_missing_inputs.csv
"""

import csv
import json
import math
import os
import sys
import warnings

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, 'outputs', 'v7_edge_ready_offline')
ARTIFACTS = os.path.join(BASE, 'artifacts', 'edge_v7')
MODEL_DIR = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'model')
SAMPLES_DIR = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'samples')


def _read_json(path):
    if not os.path.exists(path):
        return None, 'FILE_NOT_FOUND: {}'.format(path)
    with open(path, encoding='utf-8') as f:
        return json.load(f), None


def _read_csv(path):
    if not os.path.exists(path):
        return None, 'FILE_NOT_FOUND: {}'.format(path)
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f)), None


def relu(x):
    return x if x > 0.0 else 0.0


def mlp_forward_numpy(x_scaled, coefs, intercepts):
    """
    Pure numpy-equivalent MLP forward pass (simulates ESP32 C implementation).
    Uses ReLU for hidden layers, linear for output.
    """
    h = list(x_scaled)
    for layer_idx, (W, b) in enumerate(zip(coefs, intercepts)):
        n_out = len(b)
        new_h = []
        for j in range(n_out):
            val = b[j]
            for i, hi in enumerate(h):
                val += hi * W[i][j]
            if layer_idx < len(coefs) - 1:
                val = relu(val)
            new_h.append(val)
        h = new_h
    return h[0]


def apply_scaler(raw_features, data_min, scale):
    """x_scaled[i] = (raw[i] - data_min[i]) * scale[i]  — NOT clipped to [0,1]."""
    return [(raw_features[i] - data_min[i]) * scale[i] for i in range(len(raw_features))]


def clip(val, lo, hi):
    return max(lo, min(hi, val))


def collect_missing(missing):
    rows = []
    for item, reason in missing:
        rows.append({'item': item, 'reason': reason, 'status': 'MISSING_INPUT'})
    return rows


def compute_metrics(pairs):
    if not pairs:
        return {}
    n = len(pairs)
    abs_errors = [abs(p['soc_numpy'] - p['soc_ref']) for p in pairs]
    errors = [p['soc_numpy'] - p['soc_ref'] for p in pairs]
    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(e ** 2 for e in abs_errors) / n)
    ref_vals = [p['soc_ref'] for p in pairs]
    mean_ref = sum(ref_vals) / n
    ss_res = sum(e ** 2 for e in errors)
    ss_tot = sum((v - mean_ref) ** 2 for v in ref_vals)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float('nan')
    return {
        'n': n,
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'max_abs_error': max(abs_errors),
        'min_abs_error': min(abs_errors),
        'mean_bias': sum(errors) / n,
    }


def verdict_parity(mae):
    if mae < 0.001:
        return 'PASS_EXACT'
    elif mae < 0.005:
        return 'PASS_NEAR'
    elif mae < 0.05:
        return 'PASS'
    elif mae < 0.10:
        return 'WARN'
    else:
        return 'FAIL'


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    missing = []

    print('[V7A] Starting offline parity validation...')

    # --- Load feature order ---
    feature_order_path = os.path.join(ARTIFACTS, 'feature_order.json')
    feature_data, err = _read_json(feature_order_path)
    if err:
        missing.append(('feature_order.json', err))
        feature_names = ['voltage_v', 'temperature_c', 'current_ma',
                         'delta_voltage', 'delta_temperature', 'delta_current']
        print('[WARN] Using hardcoded feature order (file missing)')
    else:
        raw_feats = feature_data.get('features', [])
        feature_names = [f['name'] if isinstance(f, dict) else f for f in raw_feats]
    print('[OK] Feature order: {}'.format(feature_names))

    # --- Load scaler params ---
    scaler_path = os.path.join(ARTIFACTS, 'scaler_params.json')
    scaler_data, err = _read_json(scaler_path)
    if err:
        missing.append(('scaler_params.json', err))
        scaler_ok = False
    else:
        scaler_ok = True
        data_min = scaler_data['data_min']
        scale = scaler_data['scale']
    print('[{}] Scaler: {}'.format('OK' if scaler_ok else 'MISSING', scaler_path))

    # --- Load MLP weights ---
    weights_path = os.path.join(MODEL_DIR, 'mlp_weights.json')
    weights_data, err = _read_json(weights_path)
    if err:
        missing.append(('mlp_weights.json', err))
        model_ok = False
    else:
        model_ok = True
        coefs = weights_data['coefs']
        intercepts = weights_data['intercepts']
    print('[{}] MLP weights: {}'.format('OK' if model_ok else 'MISSING', weights_path))

    # --- Load validation inputs ---
    inputs_path = os.path.join(SAMPLES_DIR, 'export_validation_inputs.csv')
    inputs, err = _read_csv(inputs_path)
    if err:
        missing.append(('export_validation_inputs.csv', err))
        inputs = []
    print('[{}] Validation inputs: {} rows'.format(
        'OK' if inputs else 'MISSING', len(inputs)))

    # --- Load reference outputs ---
    ref_path = os.path.join(SAMPLES_DIR, 'export_validation_outputs.csv')
    ref_rows, err = _read_csv(ref_path)
    if err:
        missing.append(('export_validation_outputs.csv', err))
        ref_rows = []
    print('[{}] Reference outputs: {} rows'.format(
        'OK' if ref_rows else 'MISSING', len(ref_rows)))

    # --- Also load sklearn pipeline for cross-check ---
    pkl_path = os.path.join(MODEL_DIR, 'iot_method_b_mlp_pipeline.pkl')
    sklearn_ok = False
    pipeline = None
    if os.path.exists(pkl_path):
        try:
            import pickle
            warnings.filterwarnings('ignore')
            with open(pkl_path, 'rb') as f:
                pipeline = pickle.load(f)
            sklearn_ok = True
        except Exception as e:
            missing.append(('iot_method_b_mlp_pipeline.pkl', 'LOAD_ERROR: {}'.format(e)))
    else:
        missing.append(('iot_method_b_mlp_pipeline.pkl', 'FILE_NOT_FOUND'))
    print('[{}] sklearn pipeline: {}'.format('OK' if sklearn_ok else 'MISSING', pkl_path))

    # --- Run parity ---
    parity_rows = []
    numpy_vs_ref = []
    sklearn_vs_ref = []

    if inputs and ref_rows and scaler_ok and model_ok:
        ref_soc = [float(r['soc_pred_original']) for r in ref_rows]
        for i, inp in enumerate(inputs):
            sid = i
            try:
                raw = [float(inp[feat]) for feat in feature_names]
            except (KeyError, ValueError) as e:
                parity_rows.append({
                    'sample_id': sid, 'soc_numpy': 'ERROR', 'soc_sklearn': 'N/A',
                    'soc_ref': ref_soc[i] if i < len(ref_soc) else 'N/A',
                    'abs_error_numpy_vs_ref': 'N/A', 'abs_error_sklearn_vs_numpy': 'N/A',
                    'status': 'FEATURE_ERROR: {}'.format(e)
                })
                continue

            # Pure numpy path (ESP32 proxy)
            x_scaled = apply_scaler(raw, data_min, scale)
            soc_numpy = clip(mlp_forward_numpy(x_scaled, coefs, intercepts), 0.0, 1.0)

            # sklearn path (ground truth)
            soc_sklearn = None
            if sklearn_ok and pipeline:
                try:
                    import numpy as np
                    X_np = np.array([raw])
                    sk_scaled = pipeline['scaler'].transform(X_np)
                    sk_pred = pipeline['model'].predict(sk_scaled)[0]
                    soc_sklearn = float(np.clip(sk_pred, 0.0, 1.0))
                except Exception:
                    soc_sklearn = None

            soc_ref = ref_soc[i] if i < len(ref_soc) else None

            row = {
                'sample_id': sid,
                'soc_numpy': round(soc_numpy, 8),
                'soc_sklearn': round(soc_sklearn, 8) if soc_sklearn is not None else 'N/A',
                'soc_ref': round(soc_ref, 8) if soc_ref is not None else 'N/A',
                'abs_error_numpy_vs_ref': round(abs(soc_numpy - soc_ref), 8) if soc_ref is not None else 'N/A',
                'abs_error_sklearn_vs_numpy': round(abs(soc_numpy - soc_sklearn), 8) if soc_sklearn is not None else 'N/A',
                'status': 'OK',
            }
            parity_rows.append(row)

            if soc_ref is not None:
                numpy_vs_ref.append({'soc_numpy': soc_numpy, 'soc_ref': soc_ref})
            if soc_sklearn is not None and soc_ref is not None:
                sklearn_vs_ref.append({'soc_sklearn': soc_sklearn, 'soc_ref': soc_ref})

        print('[OK] Ran inference on {} samples'.format(len(parity_rows)))
    else:
        print('[WARN] Skipping inference — missing inputs, scaler, or model.')
        if not inputs:
            missing.append(('validation_inputs', 'Cannot run parity without input samples'))
        if not scaler_ok:
            missing.append(('scaler', 'Cannot run parity without scaler params'))
        if not model_ok:
            missing.append(('mlp_weights', 'Cannot run parity without model weights'))

    # --- Compute metrics ---
    metrics_numpy = compute_metrics(numpy_vs_ref) if numpy_vs_ref else {}
    metrics_sklearn = compute_metrics(
        [{'soc_numpy': r['soc_sklearn'], 'soc_ref': r['soc_ref']} for r in sklearn_vs_ref]
    ) if sklearn_vs_ref else {}

    parity_verdict = verdict_parity(metrics_numpy.get('mae', 999.0)) if metrics_numpy else 'NO_DATA'

    print('[V7A] Numpy inference MAE vs ref: {:.6f} — Verdict: {}'.format(
        metrics_numpy.get('mae', float('nan')), parity_verdict))

    # --- Write parity table ---
    table_path = os.path.join(OUT_DIR, 'v7_offline_parity_table.csv')
    if parity_rows:
        keys = ['sample_id', 'soc_numpy', 'soc_sklearn', 'soc_ref',
                'abs_error_numpy_vs_ref', 'abs_error_sklearn_vs_numpy', 'status']
        with open(table_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(parity_rows)
        print('[OK] Wrote: {}'.format(table_path))

    # --- Write missing inputs ---
    missing_path = os.path.join(OUT_DIR, 'v7_missing_inputs.csv')
    missing_rows = collect_missing(missing)
    with open(missing_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['item', 'reason', 'status'])
        writer.writeheader()
        writer.writerows(missing_rows)
    print('[OK] Wrote: {} ({} issues)'.format(missing_path, len(missing_rows)))

    # --- Write summary JSON ---
    summary = {
        'version': 'v7a',
        'date': '2026-05-15',
        'status': parity_verdict,
        'description': 'Offline parity: pure-numpy MLP inference vs sklearn pipeline reference',
        'methodology': {
            'numpy_path': 'Pure Python: apply_scaler() + mlp_forward_numpy() from JSON weights',
            'sklearn_path': 'sklearn Pipeline: MinMaxScaler + MLPRegressor.predict() from pkl',
            'reference': 'export_validation_outputs.csv (soc_pred_original column)',
            'note': 'This is pre-ESP32 parity. Actual ESP32 float32 may differ slightly due to precision.'
        },
        'n_samples': len(numpy_vs_ref),
        'numpy_vs_ref': metrics_numpy if metrics_numpy else {'status': 'NO_DATA'},
        'sklearn_vs_ref': metrics_sklearn if metrics_sklearn else {'status': 'NO_DATA'},
        'parity_verdict': parity_verdict,
        'parity_thresholds': {
            'PASS_EXACT': 'MAE < 0.001 (numerical identity)',
            'PASS_NEAR': 'MAE < 0.005 (within float32 precision budget)',
            'PASS': 'MAE < 0.05 (acceptable for SOC application)',
            'WARN': '0.05 <= MAE < 0.10',
            'FAIL': 'MAE >= 0.10',
        },
        'artifacts_frozen': {
            'feature_order': 'artifacts/edge_v7/feature_order.json',
            'scaler_params': 'artifacts/edge_v7/scaler_params.json',
            'model_manifest': 'artifacts/edge_v7/model_manifest.json',
        },
        'not_yet_validated': [
            'ESP32 hardware latency (gap G09)',
            'ESP32 RAM usage (gap G09)',
            'ESP32 Flash usage (gap G09)',
            'Real sensor parity (pending ESP32 run)',
            'TFLite conversion (gap G04)',
        ],
        'missing_inputs': len(missing_rows),
    }
    summary_path = os.path.join(OUT_DIR, 'v7_offline_parity_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print('[OK] Wrote: {}'.format(summary_path))

    print('')
    print('=' * 60)
    print('  V7A Offline Parity — DONE')
    print('  Samples: {}'.format(len(numpy_vs_ref)))
    if metrics_numpy:
        print('  MAE (numpy vs ref): {:.6f} SOC'.format(metrics_numpy['mae']))
        print('  RMSE (numpy vs ref): {:.6f} SOC'.format(metrics_numpy['rmse']))
        print('  R2 (numpy vs ref): {:.6f}'.format(metrics_numpy['r2']) if not math.isnan(metrics_numpy['r2']) else '  R2: N/A')
    print('  Verdict: {}'.format(parity_verdict))
    print('  Missing inputs: {}'.format(len(missing_rows)))
    print('  Outputs: {}/'.format(OUT_DIR))
    print('=' * 60)


if __name__ == '__main__':
    main()
