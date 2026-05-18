"""
v7_edge_runtime_simulator.py
V7A — Edge runtime simulator: pure Python, no pandas in main loop.

Simulates what the ESP32 firmware would do sample-by-sample:
  - Sliding window buffer (size 2 for delta computation)
  - Feature extraction (raw + deltas)
  - MinMaxScaler normalization (pure Python)
  - MLP inference (pure Python)
  - Anomaly rules (pure Python)
  - Serial-like output

Does NOT claim:
  - Real ESP32 latency or RAM measurements
  - Physical hardware validation
  - Production readiness

Input: handoff_esp32_v7/serial_replay_input_sample.csv (has pre-computed deltas)
  OR: any CSV with voltage_v, temperature_c, current_ma columns (computes deltas live)

Output: outputs/v7_edge_ready_offline/v7_serial_like_output.csv
"""

import csv
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF_V7 = os.path.join(BASE, 'handoff_esp32_v7')
ARTIFACTS = os.path.join(BASE, 'artifacts', 'edge_v7')
MODEL_DIR = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'model')
SAMPLES_DIR = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'samples')
OUT_DIR = os.path.join(BASE, 'outputs', 'v7_edge_ready_offline')


# -----------------------------------------------------------------------
# Pure-Python numeric primitives (no numpy, no pandas — ESP32 proxy)
# -----------------------------------------------------------------------

def relu_f(x):
    return x if x > 0.0 else 0.0


def clip_f(x, lo, hi):
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def scaler_transform(raw, data_min, scale):
    """MinMaxScaler: x_scaled[i] = (raw[i] - data_min[i]) * scale[i]"""
    return [(raw[i] - data_min[i]) * scale[i] for i in range(len(raw))]


def mlp_predict(x_scaled, coefs, intercepts):
    """Pure Python MLP forward pass: ReLU hidden layers, linear output."""
    h = list(x_scaled)
    for layer_idx, (W, b) in enumerate(zip(coefs, intercepts)):
        n_out = len(b)
        new_h = []
        for j in range(n_out):
            v = b[j]
            for i in range(len(h)):
                v += h[i] * W[i][j]
            if layer_idx < len(coefs) - 1:
                v = relu_f(v)
            new_h.append(v)
        h = new_h
    return h[0]


# -----------------------------------------------------------------------
# Anomaly rules (8 physical/heuristic rules, O(1) each)
# -----------------------------------------------------------------------

ANOMALY_RULES = {
    'voltage_out_of_range': {'threshold_type': 'physical', 'weight': 3.0},
    'temperature_out_of_range': {'threshold_type': 'physical', 'weight': 2.0},
    'current_out_of_range': {'threshold_type': 'physical', 'weight': 2.0},
    'abrupt_voltage': {'threshold_type': 'heuristic', 'weight': 1.5},
    'abrupt_current': {'threshold_type': 'heuristic', 'weight': 1.5},
    'abrupt_temperature': {'threshold_type': 'heuristic', 'weight': 1.0},
    'thermal_risk': {'threshold_type': 'thermal', 'weight': 2.5},
    'soc_jump': {'threshold_type': 'temporal', 'weight': 1.0},
}

SCORE_THRESHOLDS = {'NORMAL': 1.0, 'WARNING': 3.0, 'ANOMALY': 5.0}


def check_anomaly_rules(v, t, i_ma, dv, dt, di, soc, prev_soc, cfg):
    """
    Apply 8 anomaly rules. Returns (score, flag, category, active_rules).
    current_out_of_range uses A threshold from config (converted from mA input).
    """
    active = []
    score = 0.0

    if v < cfg['voltage_min_V'] or v > cfg['voltage_max_V']:
        active.append('voltage_out_of_range')
        score += 3.0

    if t < cfg['temp_min_C'] or t > cfg['temp_max_C']:
        active.append('temperature_out_of_range')
        score += 2.0

    i_a = i_ma / 1000.0
    if abs(i_a) > cfg['current_max_A']:
        active.append('current_out_of_range')
        score += 2.0

    if abs(dv) > cfg['delta_voltage_threshold']:
        active.append('abrupt_voltage')
        score += 1.5

    di_a = di / 1000.0
    if abs(di_a) > cfg['delta_current_threshold']:
        active.append('abrupt_current')
        score += 1.5

    if abs(dt) > cfg['delta_temp_threshold']:
        active.append('abrupt_temperature')
        score += 1.0

    delta_t_pos = dt > cfg['thermal_delta_threshold_C']
    i_high = abs(i_a) > cfg['thermal_current_threshold_A']
    if delta_t_pos and i_high:
        active.append('thermal_risk')
        score += 2.5

    if prev_soc is not None and abs(soc - prev_soc) > cfg['max_soc_jump_per_sample']:
        active.append('soc_jump')
        score += 1.0

    flag = 1 if score >= SCORE_THRESHOLDS['NORMAL'] else 0
    if score >= SCORE_THRESHOLDS['ANOMALY']:
        category = 'ANOMALY' if score < SCORE_THRESHOLDS['ANOMALY'] else 'ANOMALY'
    if score >= 5.0:
        category = 'CRITICAL'
    elif score >= 3.0:
        category = 'ANOMALY'
    elif score >= 1.0:
        category = 'WARNING'
    else:
        category = 'NORMAL'

    return score, flag, category, active


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_csv(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print('[V7A-SIM] Starting edge runtime simulator...')

    # --- Load artifacts ---
    scaler_data = load_json(os.path.join(ARTIFACTS, 'scaler_params.json'))
    if scaler_data is None:
        print('[ERROR] scaler_params.json not found. Run v7_edge_ready_offline_parity.py first.')
        sys.exit(1)
    data_min = scaler_data['data_min']
    scale_vec = scaler_data['scale']

    weights_data = load_json(os.path.join(MODEL_DIR, 'mlp_weights.json'))
    model_available = weights_data is not None
    if model_available:
        coefs = weights_data['coefs']
        intercepts = weights_data['intercepts']
        print('[OK] MLP weights loaded: {} layers'.format(len(coefs)))
    else:
        print('[WARN] mlp_weights.json not found — soc_predicted will be MISSING_MODEL')

    cfg_data = load_json(os.path.join(BASE, 'outputs', 'offline_anomaly', 'v4', 'anomaly_config_v4.json'))
    if cfg_data is None:
        cfg_data = {
            'voltage_min_V': 2.5, 'voltage_max_V': 4.25,
            'temp_min_C': -20.0, 'temp_max_C': 60.0,
            'current_max_A': 20.0, 'delta_voltage_threshold': 0.679,
            'delta_current_threshold': 3.53, 'delta_temp_threshold': 9.3,
            'max_soc_jump_per_sample': 0.05,
            'thermal_delta_threshold_C': 2.0, 'thermal_current_threshold_A': 3.0,
        }
        print('[WARN] anomaly_config_v4.json not found — using hardcoded defaults')
    else:
        print('[OK] Anomaly config loaded from v4')

    # --- Load reference SOC for comparison ---
    ref_rows = load_csv(os.path.join(SAMPLES_DIR, 'export_validation_inputs.csv'))
    ref_outs = load_csv(os.path.join(SAMPLES_DIR, 'export_validation_outputs.csv'))
    ref_soc_map = {}
    if ref_outs:
        for idx, r in enumerate(ref_outs):
            ref_soc_map[idx] = float(r['soc_pred_original'])

    # --- Load replay input ---
    replay_path = os.path.join(HANDOFF_V7, 'serial_replay_input_sample.csv')
    replay_rows = load_csv(replay_path)
    if replay_rows is None:
        print('[ERROR] Replay input CSV not found: {}'.format(replay_path))
        sys.exit(1)
    print('[OK] Replay input: {} rows'.format(len(replay_rows)))

    feature_names = ['voltage_v', 'temperature_c', 'current_ma',
                     'delta_voltage', 'delta_temperature', 'delta_current']

    # --- Main simulation loop (no pandas, pure Python, small buffer) ---
    output_rows = []
    prev_soc = None
    prev_v = None
    prev_t = None
    prev_i = None

    FEATURE_INDEX = {name: i for i, name in enumerate(feature_names)}

    for row_idx, row in enumerate(replay_rows):
        sample_id = int(row.get('sample_id', row_idx))
        status_parts = []

        # --- Parse raw signals ---
        try:
            v = float(row['voltage_v'])
            t = float(row['temperature_c'])
            i_ma = float(row['current_ma'])
        except (KeyError, ValueError) as e:
            output_rows.append({
                'timestamp': sample_id,
                'voltage_v': row.get('voltage_v', 'N/A'),
                'current_ma': row.get('current_ma', 'N/A'),
                'temperature_c': row.get('temperature_c', 'N/A'),
                'soc_predicted': 'PARSE_ERROR',
                'soc_reference': '',
                'anomaly_flag': 0,
                'anomaly_score': 0.0,
                'anomaly_reason': '',
                'status': 'PARSE_ERROR:{}'.format(e),
            })
            continue

        # --- Delta computation (use CSV-provided if available, else compute from buffer) ---
        if 'delta_voltage' in row and row['delta_voltage'] not in ('', 'N/A'):
            try:
                dv = float(row['delta_voltage'])
                dt_f = float(row['delta_temperature'])
                di = float(row['delta_current'])
            except (ValueError, KeyError):
                dv = (v - prev_v) if prev_v is not None else 0.0
                dt_f = (t - prev_t) if prev_t is not None else 0.0
                di = (i_ma - prev_i) if prev_i is not None else 0.0
        else:
            dv = (v - prev_v) if prev_v is not None else 0.0
            dt_f = (t - prev_t) if prev_t is not None else 0.0
            di = (i_ma - prev_i) if prev_i is not None else 0.0

        # Update buffer
        prev_v = v
        prev_t = t
        prev_i = i_ma

        # --- Input validation (REJECT/WARN) ---
        rejected = False
        if v < 3.5 or v > 4.4:
            status_parts.append('WARN_VOLTAGE_RANGE')
        if t < -10.0 or t > 60.0:
            status_parts.append('WARN_TEMP_RANGE')
        if i_ma < 10.0 or i_ma > 350.0:
            status_parts.append('WARN_CURRENT_RANGE')
        if abs(dv) > 0.5:
            status_parts.append('WARN_LARGE_DELTA_V')
        if abs(dt_f) > 50.0:
            status_parts.append('WARN_LARGE_DELTA_T')

        # --- Feature vector ---
        raw = [v, t, i_ma, dv, dt_f, di]

        # --- Scaler + MLP ---
        if model_available:
            x_scaled = scaler_transform(raw, data_min, scale_vec)
            soc_raw = mlp_predict(x_scaled, coefs, intercepts)
            soc_pred = clip_f(soc_raw, 0.0, 1.0)
            soc_str = round(soc_pred, 6)
        else:
            soc_pred = None
            soc_str = 'MISSING_MODEL'

        # --- Anomaly rules ---
        score, flag, category, active_rules = check_anomaly_rules(
            v, t, i_ma, dv, dt_f, di,
            soc_pred if soc_pred is not None else 0.5,
            prev_soc, cfg_data
        )
        prev_soc = soc_pred

        # --- Reference SOC (from validation outputs if available) ---
        soc_ref = ref_soc_map.get(row_idx, '')

        status_final = '|'.join(status_parts) if status_parts else 'OK'

        output_rows.append({
            'timestamp': sample_id,
            'voltage_v': round(v, 6),
            'current_ma': round(i_ma, 6),
            'temperature_c': round(t, 6),
            'soc_predicted': soc_str,
            'soc_reference': round(soc_ref, 6) if isinstance(soc_ref, float) else '',
            'anomaly_flag': flag,
            'anomaly_score': round(score, 4),
            'anomaly_reason': '|'.join(active_rules) if active_rules else 'NORMAL',
            'status': status_final,
        })

    # --- Write output ---
    out_path = os.path.join(OUT_DIR, 'v7_serial_like_output.csv')
    fieldnames = ['timestamp', 'voltage_v', 'current_ma', 'temperature_c',
                  'soc_predicted', 'soc_reference', 'anomaly_flag',
                  'anomaly_score', 'anomaly_reason', 'status']
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    # --- Stats ---
    n_anomaly = sum(1 for r in output_rows if r['anomaly_flag'] == 1)
    n_ok = sum(1 for r in output_rows if r['status'] == 'OK')
    print('[OK] Wrote: {} ({} rows)'.format(out_path, len(output_rows)))
    print('[V7A-SIM] Samples: {} | Anomaly flags: {} | Status OK: {}'.format(
        len(output_rows), n_anomaly, n_ok))
    print('[NOTE] Latency/RAM/Flash NOT simulated — pending real ESP32 run (gap G09)')


if __name__ == '__main__':
    main()
