"""
V7C — Canonical Method B Model Training Script.
Trains Ridge, MLP-small (32/16), and MLP-canonical (64/32) on the IoT Method B dataset
using Leave-One-Node-Out (LONO) cross-validation.
Generates: v7c_model_benchmark.csv, v7c_split_validation_results.csv,
           v7c_feature_ablation.csv, canonical_scaler_params.json,
           canonical_model_weights.json.
"""

import csv
import json
import os
import pickle
import math

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'outputs', 'v7c_canonical_method_b_artifact')
ART = os.path.join(BASE, 'artifacts', 'edge_v7c')
PARQUET = os.path.join(BASE, 'outputs', 'external_datasets', 'iot_method_b_extracted.parquet')
MISSING = []

os.makedirs(OUT, exist_ok=True)
os.makedirs(ART, exist_ok=True)


def _check(path, label):
    if not os.path.exists(path):
        MISSING.append(label + ': ' + path)
        return False
    return True


_check(PARQUET, 'iot_method_b_extracted.parquet')
if MISSING:
    print('[V7C] MISSING inputs:')
    for m in MISSING:
        print('  ', m)
    raise SystemExit(1)


import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler

FEATURES = ['voltage_v', 'temperature_c', 'current_ma',
            'delta_voltage', 'delta_temperature', 'delta_current']
TARGET = 'soc_method_b'
NODE_COL = 'node_id'
RANDOM_STATE = 42


NODES_V1 = [13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9, 14.0, 14.1, 14.2, 14.3]


def _load_dataset():
    df = pd.read_parquet(PARQUET)
    if TARGET not in df.columns:
        alt = [c for c in df.columns if 'soc_method_b' in c]
        if alt:
            df = df.rename(columns={alt[0]: TARGET})
        else:
            raise ValueError('No soc_method_b column. Columns: ' + str(list(df.columns)))
    if NODE_COL not in df.columns:
        alt = [c for c in df.columns if 'node' in c.lower()]
        if alt:
            df = df.rename(columns={alt[0]: NODE_COL})
        else:
            df[NODE_COL] = 0

    # Filter to V1 training subset: 13 nodes, discharging only
    df = df[df[NODE_COL].isin(NODES_V1)].copy()
    if 'is_discharging' in df.columns:
        df = df[df['is_discharging'] == True].copy()

    # Compute delta features within each node (sorted by time if datetime available)
    if 'datetime' in df.columns:
        df = df.sort_values([NODE_COL, 'datetime']).reset_index(drop=True)
    else:
        df = df.sort_values(NODE_COL).reset_index(drop=True)

    for col, delta_col in [('voltage_v', 'delta_voltage'),
                            ('temperature_c', 'delta_temperature'),
                            ('current_ma', 'delta_current')]:
        df[delta_col] = df.groupby(NODE_COL)[col].diff().fillna(0.0)

    df = df.dropna(subset=FEATURES + [TARGET])
    return df


def _r2(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return 1.0 - ss_res / ss_tot


def _mae(y_true, y_pred):
    return float(np.mean(np.abs(np.array(y_true) - np.array(y_pred))))


def _rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((np.array(y_true) - np.array(y_pred)) ** 2)))


def _get_models():
    ridge = Ridge(alpha=1.0)
    mlp_small = MLPRegressor(
        hidden_layer_sizes=(32, 16),
        activation='relu',
        solver='adam',
        max_iter=300,
        random_state=RANDOM_STATE,
        early_stopping=False
    )
    mlp_canonical = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        activation='relu',
        solver='adam',
        max_iter=300,
        random_state=RANDOM_STATE,
        early_stopping=False
    )
    return [
        ('Ridge', ridge),
        ('MLP-small-32-16', mlp_small),
        ('MLP-canonical-64-32', mlp_canonical),
    ]


def _lono_cv(df, model_factory_list, features, target, node_col):
    nodes = sorted(df[node_col].unique())
    results = []
    per_node = []

    for model_name, model_template in model_factory_list:
        all_y_true = []
        all_y_pred = []
        for node in nodes:
            test_mask = df[node_col] == node
            train_mask = ~test_mask
            X_train = df.loc[train_mask, features].values
            y_train = df.loc[train_mask, target].values
            X_test = df.loc[test_mask, features].values
            y_test = df.loc[test_mask, target].values

            scaler = MinMaxScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            import copy
            m = copy.deepcopy(model_template)
            m.fit(X_train_s, y_train)
            y_pred = np.clip(m.predict(X_test_s), 0.0, 1.0)

            r2_node = _r2(y_test, y_pred)
            mae_node = _mae(y_test, y_pred)
            rmse_node = _rmse(y_test, y_pred)

            per_node.append({
                'model': model_name,
                'node': node,
                'train_rows': int(train_mask.sum()),
                'test_rows': int(test_mask.sum()),
                'R2': round(r2_node, 4),
                'MAE': round(mae_node, 4),
                'RMSE': round(rmse_node, 4),
                'bias': round(float(np.mean(y_pred - y_test)), 4),
            })
            all_y_true.extend(y_test.tolist())
            all_y_pred.extend(y_pred.tolist())

        lono_r2 = _r2(all_y_true, all_y_pred)
        lono_mae = _mae(all_y_true, all_y_pred)
        lono_rmse = _rmse(all_y_true, all_y_pred)
        results.append({
            'model': model_name,
            'validation': 'LONO',
            'n_nodes': len(nodes),
            'n_rows': len(all_y_true),
            'R2_LONO': round(lono_r2, 4),
            'MAE_LONO': round(lono_mae, 4),
            'RMSE_LONO': round(lono_rmse, 4),
        })
        print('[V7C] {} LONO: R2={:.4f} MAE={:.4f}'.format(model_name, lono_r2, lono_mae))

    return results, per_node


def _train_final_canonical(df, features, target):
    """Train canonical model on full dataset for weight export."""
    X = df[features].values
    y = df[target].values
    scaler = MinMaxScaler()
    X_s = scaler.fit_transform(X)
    model = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        activation='relu',
        solver='adam',
        max_iter=300,
        random_state=RANDOM_STATE,
        early_stopping=False
    )
    model.fit(X_s, y)
    return model, scaler


def _export_weights(model, scaler, features):
    """Export MLP weights in V7B-compatible structured format."""
    coefs = model.coefs_
    intercepts = model.intercepts_
    layers = []
    for i, (W, b) in enumerate(zip(coefs, intercepts)):
        activation = 'relu' if i < len(coefs) - 1 else 'linear'
        layers.append({
            'layer_index': i,
            'input_size': int(W.shape[0]),
            'output_size': int(W.shape[1]),
            'activation': activation,
            'weights': W.tolist(),
            'biases': b.tolist(),
        })
    total_params = sum(W.shape[0] * W.shape[1] + len(b) for W, b in zip(coefs, intercepts))

    data_min = scaler.data_min_.tolist()
    data_max = scaler.data_max_.tolist()
    scale = scaler.scale_.tolist()

    weights_doc = {
        'version': 'v7c',
        'date': '2026-05-15',
        'status': 'CANONICAL_FROZEN',
        'model_id': 'iot_method_b_mlp_canonical_v7c',
        'architecture': 'Input(6) -> Hidden(64, ReLU) -> Hidden(32, ReLU) -> Output(1, linear)',
        'feature_names': features,
        'total_parameters': int(total_params),
        'scaler': {
            'type': 'MinMaxScaler',
            'data_min': data_min,
            'data_max': data_max,
            'scale': scale,
        },
        'layers': layers,
    }
    return weights_doc, data_min, data_max, scale


def _export_c_header(weights_doc, out_path):
    """Generate C header preview for ESP32 firmware."""
    features = weights_doc['feature_names']
    scaler = weights_doc['scaler']
    layers = weights_doc['layers']
    n_features = len(features)

    lines = [
        '/* V7C Canonical MLP Weights — PREVIEW ONLY. Not final firmware artifact. */',
        '/* Generated: 2026-05-15 | Architecture: Input(6)->64->32->1 | Params: {} */'.format(
            weights_doc['total_parameters']),
        '#ifndef IOT_MLP_CANONICAL_WEIGHTS_H',
        '#define IOT_MLP_CANONICAL_WEIGHTS_H',
        '',
        '#define MLP_INPUT_SIZE {}'.format(n_features),
        '#define MLP_L0_SIZE 64',
        '#define MLP_L1_SIZE 32',
        '#define MLP_OUTPUT_SIZE 1',
        '',
        '/* MinMaxScaler: x_scaled[i] = (x[i] - SCALER_MIN[i]) * SCALER_SCALE[i] */',
        'static const float SCALER_MIN[{}] = {{'.format(n_features),
        '  ' + ', '.join('{:.8f}f'.format(v) for v in scaler['data_min']) + '',
        '};',
        'static const float SCALER_SCALE[{}] = {{'.format(n_features),
        '  ' + ', '.join('{:.8f}f'.format(v) for v in scaler['scale']) + '',
        '};',
        '',
        '/* Layer 0: {}x{} weights */' .format(layers[0]['input_size'], layers[0]['output_size']),
        'static const float W0[{}][{}] = {{'.format(layers[0]['input_size'], layers[0]['output_size']),
    ]
    for row in layers[0]['weights']:
        lines.append('  {' + ', '.join('{:.8f}f'.format(v) for v in row) + '},')
    lines += [
        '};',
        'static const float B0[{}] = {{'.format(layers[0]['output_size']),
        '  ' + ', '.join('{:.8f}f'.format(v) for v in layers[0]['biases']) + '',
        '};',
        '',
        '/* Layer 1: {}x{} weights */'.format(layers[1]['input_size'], layers[1]['output_size']),
        'static const float W1[{}][{}] = {{'.format(layers[1]['input_size'], layers[1]['output_size']),
    ]
    for row in layers[1]['weights']:
        lines.append('  {' + ', '.join('{:.8f}f'.format(v) for v in row) + '},')
    lines += [
        '};',
        'static const float B1[{}] = {{'.format(layers[1]['output_size']),
        '  ' + ', '.join('{:.8f}f'.format(v) for v in layers[1]['biases']) + '',
        '};',
        '',
        '/* Layer 2 (output): {}x{} weights */'.format(layers[2]['input_size'], layers[2]['output_size']),
        'static const float W2[{}][{}] = {{'.format(layers[2]['input_size'], layers[2]['output_size']),
    ]
    for row in layers[2]['weights']:
        lines.append('  {' + ', '.join('{:.8f}f'.format(v) for v in row) + '},')
    lines += [
        '};',
        'static const float B2[{}] = {{'.format(layers[2]['output_size']),
        '  ' + ', '.join('{:.8f}f'.format(v) for v in layers[2]['biases']) + '',
        '};',
        '',
        '/* ReLU activation: fmaxf(0.0f, x) */',
        '/* Output clip: fmaxf(0.0f, fminf(1.0f, output)) */',
        '',
        '#endif /* IOT_MLP_CANONICAL_WEIGHTS_H */',
    ]
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def _feature_ablation(df, target, node_col):
    """Run LONO ablation study: drop one feature at a time + baseline (all 6)."""
    import copy
    results = []
    feature_sets = [
        ('all_6', FEATURES),
        ('drop_temperature_c', [f for f in FEATURES if f != 'temperature_c']),
        ('drop_voltage_v', [f for f in FEATURES if f != 'voltage_v']),
        ('drop_current_ma', [f for f in FEATURES if f != 'current_ma']),
        ('drop_delta_voltage', [f for f in FEATURES if f != 'delta_voltage']),
        ('drop_delta_temperature', [f for f in FEATURES if f != 'delta_temperature']),
        ('drop_delta_current', [f for f in FEATURES if f != 'delta_current']),
        ('only_primary_3', ['voltage_v', 'temperature_c', 'current_ma']),
        ('only_deltas_3', ['delta_voltage', 'delta_temperature', 'delta_current']),
    ]
    nodes = sorted(df[node_col].unique())
    for subset_name, feats in feature_sets:
        all_y_true = []
        all_y_pred = []
        for node in nodes:
            test_mask = df[node_col] == node
            train_mask = ~test_mask
            X_train = df.loc[train_mask, feats].values
            y_train = df.loc[train_mask, target].values
            X_test = df.loc[test_mask, feats].values
            y_test = df.loc[test_mask, target].values
            scaler = MinMaxScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)
            m = MLPRegressor(
                hidden_layer_sizes=(64, 32),
                activation='relu',
                solver='adam',
                max_iter=200,
                random_state=RANDOM_STATE,
            )
            m.fit(X_train_s, y_train)
            y_pred = np.clip(m.predict(X_test_s), 0.0, 1.0)
            all_y_true.extend(y_test.tolist())
            all_y_pred.extend(y_pred.tolist())
        r2_lono = _r2(all_y_true, all_y_pred)
        mae_lono = _mae(all_y_true, all_y_pred)
        dropped = 'none' if subset_name == 'all_6' else ', '.join(
            f for f in FEATURES if f not in feats)
        results.append({
            'subset_name': subset_name,
            'n_features': len(feats),
            'features_included': ','.join(feats),
            'features_dropped': dropped if dropped else 'none',
            'R2_LONO': round(r2_lono, 4),
            'MAE_LONO': round(mae_lono, 4),
            'vs_all6_R2_delta': '',
        })
        print('[V7C] Ablation {} ({}f): R2={:.4f}'.format(subset_name, len(feats), r2_lono))
    # Fill delta vs baseline
    baseline_r2 = next(r['R2_LONO'] for r in results if r['subset_name'] == 'all_6')
    for r in results:
        r['vs_all6_R2_delta'] = round(r['R2_LONO'] - baseline_r2, 4)
    return results


def _write_csv(path, rows, fieldnames=None):
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    print('[V7C] Loading dataset...')
    df = _load_dataset()
    print('[V7C] Dataset: {} rows, {} nodes, columns: {}'.format(
        len(df), df[NODE_COL].nunique(), list(df.columns[:10])))

    # --- LONO benchmark ---
    print('[V7C] Running LONO cross-validation...')
    models = _get_models()
    lono_results, per_node_results = _lono_cv(df, models, FEATURES, TARGET, NODE_COL)

    benchmark_path = os.path.join(OUT, 'v7c_model_benchmark.csv')
    _write_csv(benchmark_path, lono_results)
    print('[V7C] Wrote:', benchmark_path)

    split_path = os.path.join(OUT, 'v7c_split_validation_results.csv')
    # Add placeholder rows for unavailable split types — use same fields as per_node_results
    per_node_results.extend([
        {'model': 'ALL_MODELS', 'node': 'LOCO_NOT_APPLICABLE', 'train_rows': 'N/A',
         'test_rows': 'N/A', 'R2': 'N/A', 'MAE': 'N/A', 'RMSE': 'N/A', 'bias': 'LOCO not applicable — IoT nodes are time series without per-cycle ordering'},
        {'model': 'ALL_MODELS', 'node': 'LOTO_NOT_DONE', 'train_rows': 'N/A',
         'test_rows': 'N/A', 'R2': 'N/A', 'MAE': 'N/A', 'RMSE': 'N/A', 'bias': 'LOTO not applicable — IoT dataset lacks temperature regime labels'},
        {'model': 'ALL_MODELS', 'node': 'CROSS_DATASET_NOT_DONE', 'train_rows': 'N/A',
         'test_rows': 'N/A', 'R2': 'N/A', 'MAE': 'N/A', 'RMSE': 'N/A', 'bias': 'Cross-dataset evaluation PENDING Phase 3C (Oxford/McMaster different chemistry)'},
    ])
    _write_csv(split_path, per_node_results)
    print('[V7C] Wrote:', split_path)

    # --- Feature ablation ---
    print('[V7C] Running feature ablation...')
    ablation_results = _feature_ablation(df, TARGET, NODE_COL)
    ablation_path = os.path.join(OUT, 'v7c_feature_ablation.csv')
    _write_csv(ablation_path, ablation_results)
    print('[V7C] Wrote:', ablation_path)

    # --- Train canonical model on full dataset ---
    print('[V7C] Training canonical MLP-64-32 on full dataset for weight export...')
    canonical_model, canonical_scaler = _train_final_canonical(df, FEATURES, TARGET)

    # Export scaler params
    scaler_doc = {
        'version': 'v7c',
        'date': '2026-05-15',
        'status': 'CANONICAL_FROZEN',
        'type': 'MinMaxScaler',
        'provenance': 'Fit on full IoT energy harvesting dataset (4463 rows). Re-derived in V7C canonical training.',
        'v1_crosscheck': 'Compare with V7A scaler_params.json. Small differences expected from train/test split vs full dataset.',
        'formula': 'x_scaled[i] = (raw[i] - data_min[i]) * scale[i]',
        'formula_note': 'Do NOT clip x_scaled. Only clip final SOC: soc = clip(mlp_output, 0.0, 1.0)',
        'feature_names': FEATURES,
        'data_min': canonical_scaler.data_min_.tolist(),
        'data_max': canonical_scaler.data_max_.tolist(),
        'scale': canonical_scaler.scale_.tolist(),
        'pending_validation': {
            'esp32_hardware_benchmark': 'NOT_DONE — RAM/Flash/latency not yet measured on real hardware',
            'real_sensor_parity': 'NOT_DONE — requires ESP32 run with physical sensor',
        }
    }
    scaler_path = os.path.join(ART, 'canonical_scaler_params.json')
    with open(scaler_path, 'w', encoding='utf-8') as f:
        json.dump(scaler_doc, f, indent=2)
    print('[V7C] Wrote:', scaler_path)

    # Export weights
    weights_doc, data_min, data_max, scale = _export_weights(canonical_model, canonical_scaler, FEATURES)
    weights_path = os.path.join(ART, 'canonical_model_weights.json')
    with open(weights_path, 'w', encoding='utf-8') as f:
        json.dump(weights_doc, f, indent=2)
    print('[V7C] Wrote:', weights_path)

    # Export C header
    header_path = os.path.join(ART, 'canonical_model_weights_preview.h')
    _export_c_header(weights_doc, header_path)
    print('[V7C] Wrote:', header_path)

    # Save canonical pkl for parity verification
    canonical_pkl_path = os.path.join(ART, 'canonical_mlp_pipeline.pkl')
    with open(canonical_pkl_path, 'wb') as f:
        pickle.dump({'scaler': canonical_scaler, 'model': canonical_model, 'features': FEATURES}, f)
    print('[V7C] Wrote:', canonical_pkl_path)

    # Save metrics summary
    canonical_lono = next((r for r in lono_results if 'canonical' in r['model']), None)
    v1_r2 = 0.8087
    v1_mae = 0.1665
    if canonical_lono:
        r2_canonical = canonical_lono['R2_LONO']
        mae_canonical = canonical_lono['MAE_LONO']
    else:
        r2_canonical = None
        mae_canonical = None

    verdict = 'UNKNOWN'
    if r2_canonical is not None:
        if r2_canonical >= v1_r2 - 0.02:
            verdict = 'CANONICAL_MODEL_APPROVED_FOR_ESP_HANDOFF'
        else:
            verdict = 'LEGACY_MODEL_ONLY_FOR_TECHNICAL_HANDOFF'

    summary = {
        'version': 'v7c',
        'date': '2026-05-15',
        'dataset': 'IoT energy harvesting — {}_rows {}_nodes LONO'.format(len(df), df[NODE_COL].nunique()),
        'target': 'soc_method_b',
        'features': FEATURES,
        'models_trained': [r['model'] for r in lono_results],
        'benchmark': {r['model']: {'R2_LONO': r['R2_LONO'], 'MAE_LONO': r['MAE_LONO']} for r in lono_results},
        'v1_reference': {'R2_LONO': v1_r2, 'MAE_LONO': v1_mae},
        'canonical_vs_v1_R2_delta': round(r2_canonical - v1_r2, 4) if r2_canonical else None,
        'verdict': verdict,
        'verdict_threshold': 'R2_canonical >= R2_v1 - 0.02 (parity threshold)',
    }
    summary_path = os.path.join(OUT, 'v7c_training_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print('[V7C] Wrote:', summary_path)
    print('[V7C] Canonical R2={} | V1 R2={} | Verdict: {}'.format(r2_canonical, v1_r2, verdict))

    return summary


if __name__ == '__main__':
    result = main()
    print('\n[V7C] Training complete.')
    print('  Verdict:', result['verdict'])
    print('  Canonical R2:', result['benchmark'].get('MLP-canonical-64-32', {}).get('R2_LONO', 'N/A'))
    print('  V1 Reference R2:', result['v1_reference']['R2_LONO'])
