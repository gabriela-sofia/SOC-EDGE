"""
v7_fault_injection_offline.py
V7A — Offline fault injection: apply 8 synthetic scenarios to baseline samples,
run anomaly rules, measure detection rate and delay.

Does NOT use real fault data. All scenarios are synthetic.
Results are NOT ground truth for production anomaly detection.

Scenarios:
  1. voltage_spike         — sudden voltage above 4.25 V
  2. current_spike         — sudden current above 20 A (20000 mA)
  3. temperature_jump      — sudden temperature jump > 9.3 C in one step
  4. voltage_flatline      — voltage constant for N steps (delta_v = 0)
  5. current_dropout       — current drops to near 0 suddenly
  6. noise_burst           — all signals get Gaussian-like noise (synthetic)
  7. soc_temporal_incoherence — SOC changes by > 0.05 per step
  8. domain_shift_current_scale — current scaled by Oxford factor (/ 1000 to A then back)

Output:
  outputs/v7_edge_ready_offline/v7_fault_injection_results.csv
"""

import csv
import json
import math
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS = os.path.join(BASE, 'artifacts', 'edge_v7')
MODEL_DIR = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'model')
SAMPLES_DIR = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'samples')
REPLAY_PATH = os.path.join(BASE, 'handoff_esp32_v7', 'serial_replay_input_sample.csv')
OUT_DIR = os.path.join(BASE, 'outputs', 'v7_edge_ready_offline')


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


def clip_f(x, lo, hi):
    return max(lo, min(hi, x))


def relu_f(x):
    return x if x > 0.0 else 0.0


def scaler_transform(raw, data_min, scale_vec):
    return [(raw[i] - data_min[i]) * scale_vec[i] for i in range(len(raw))]


def mlp_predict(x_scaled, coefs, intercepts):
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


def check_rules(v, t, i_ma, dv, dt, di, soc, prev_soc, cfg):
    active = []
    score = 0.0
    if v < cfg['voltage_min_V'] or v > cfg['voltage_max_V']:
        active.append('voltage_out_of_range')
        score += 3.0
    if t < cfg['temp_min_C'] or t > cfg['temp_max_C']:
        active.append('temperature_out_of_range')
        score += 2.0
    if abs(i_ma / 1000.0) > cfg['current_max_A']:
        active.append('current_out_of_range')
        score += 2.0
    if abs(dv) > cfg['delta_voltage_threshold']:
        active.append('abrupt_voltage')
        score += 1.5
    if abs(di / 1000.0) > cfg['delta_current_threshold']:
        active.append('abrupt_current')
        score += 1.5
    if abs(dt) > cfg['delta_temp_threshold']:
        active.append('abrupt_temperature')
        score += 1.0
    if dt > cfg['thermal_delta_threshold_C'] and abs(i_ma / 1000.0) > cfg['thermal_current_threshold_A']:
        active.append('thermal_risk')
        score += 2.5
    if prev_soc is not None and abs(soc - prev_soc) > cfg['max_soc_jump_per_sample']:
        active.append('soc_jump')
        score += 1.0
    flag = 1 if score >= 1.0 else 0
    return score, flag, active


def run_scenario(name, samples, inject_fn, cfg, scaler, weights, feature_names, inject_start=5, inject_len=10):
    """
    Apply inject_fn to samples[inject_start:inject_start+inject_len].
    Returns (n_samples, n_flags, flag_rate, detection_delay, fp_count, status, notes).
    """
    n = len(samples)
    flags = []
    first_detect = None
    prev_soc = None
    scaler_ok = scaler is not None
    model_ok = weights is not None

    for idx, row in enumerate(samples):
        try:
            v = float(row['voltage_v'])
            t = float(row['temperature_c'])
            i_ma = float(row['current_ma'])
            dv = float(row.get('delta_voltage', 0.0))
            dt = float(row.get('delta_temperature', 0.0))
            di = float(row.get('delta_current', 0.0))
        except (ValueError, KeyError):
            flags.append(0)
            continue

        in_fault_zone = inject_start <= idx < inject_start + inject_len
        if in_fault_zone:
            v, t, i_ma, dv, dt, di = inject_fn(v, t, i_ma, dv, dt, di, idx)

        raw = [v, t, i_ma, dv, dt, di]
        if scaler_ok and model_ok:
            x_scaled = scaler_transform(raw, scaler['data_min'], scaler['scale'])
            soc = clip_f(mlp_predict(x_scaled, weights['coefs'], weights['intercepts']), 0.0, 1.0)
        else:
            soc = 0.5

        score, flag, active = check_rules(v, t, i_ma, dv, dt, di, soc, prev_soc, cfg)
        prev_soc = soc
        flags.append(flag)

        if flag and first_detect is None and in_fault_zone:
            first_detect = idx - inject_start

    injected_flags = flags[inject_start:inject_start + inject_len]
    pre_flags = flags[:inject_start]
    post_flags = flags[inject_start + inject_len:]

    n_injected = len(injected_flags)
    flag_count = sum(injected_flags)
    flag_rate = flag_count / n_injected if n_injected > 0 else 0.0
    detection_delay = first_detect if first_detect is not None else -1
    fp_count = sum(pre_flags) + sum(post_flags)

    status = 'DETECTED' if flag_rate > 0 else 'MISSED'
    return {
        'scenario': name,
        'samples': n,
        'injected_samples': n_injected,
        'anomaly_flags_in_fault_zone': flag_count,
        'flag_rate': round(flag_rate, 4),
        'detection_delay_samples': detection_delay,
        'false_positives_outside_fault': fp_count,
        'false_positive_context': 'samples outside fault zone [0:{}) + [{}:{})'.format(
            inject_start, inject_start + inject_len, n),
        'status': status,
        'notes': '',
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print('[V7A-FAULT] Starting offline fault injection...')

    scaler = load_json(os.path.join(ARTIFACTS, 'scaler_params.json'))
    weights = load_json(os.path.join(MODEL_DIR, 'mlp_weights.json'))
    cfg = load_json(os.path.join(BASE, 'outputs', 'offline_anomaly', 'v4', 'anomaly_config_v4.json'))
    if cfg is None:
        cfg = {
            'voltage_min_V': 2.5, 'voltage_max_V': 4.25,
            'temp_min_C': -20.0, 'temp_max_C': 60.0,
            'current_max_A': 20.0, 'delta_voltage_threshold': 0.679,
            'delta_current_threshold': 3.53, 'delta_temp_threshold': 9.3,
            'max_soc_jump_per_sample': 0.05,
            'thermal_delta_threshold_C': 2.0, 'thermal_current_threshold_A': 3.0,
        }

    feature_names = ['voltage_v', 'temperature_c', 'current_ma',
                     'delta_voltage', 'delta_temperature', 'delta_current']

    # Load base samples (use only normal rows from replay)
    replay = load_csv(REPLAY_PATH)
    if replay is None:
        # Fallback: build synthetic normal baseline
        print('[WARN] Replay CSV not found — using synthetic baseline')
        base_samples = []
        for i in range(40):
            v0 = 4.15 - i * 0.005
            base_samples.append({
                'voltage_v': str(v0), 'temperature_c': '25.0',
                'current_ma': '185.0', 'delta_voltage': '-0.005',
                'delta_temperature': '0.0', 'delta_current': '0.0',
            })
    else:
        base_samples = [r for r in replay if r.get('anomaly_injected', '0') == '0']
        print('[OK] Normal baseline: {} rows'.format(len(base_samples)))

    # Extend baseline if needed
    while len(base_samples) < 30:
        base_samples = base_samples + base_samples
    base_samples = base_samples[:40]

    results = []

    # --- Scenario 1: voltage_spike ---
    def inj_voltage_spike(v, t, i, dv, dt, di, idx):
        return 4.60, t, i, dv + 0.45, dt, di
    r = run_scenario('voltage_spike', [dict(s) for s in base_samples], inj_voltage_spike,
                     cfg, scaler, weights, feature_names)
    r['notes'] = 'voltage set to 4.60 V (above max 4.25 V) — triggers voltage_out_of_range'
    results.append(r)

    # --- Scenario 2: current_spike ---
    def inj_current_spike(v, t, i, dv, dt, di, idx):
        return v, t, 25000.0, dv, dt, 25000.0 - i
    r = run_scenario('current_spike', [dict(s) for s in base_samples], inj_current_spike,
                     cfg, scaler, weights, feature_names)
    r['notes'] = 'current set to 25000 mA (25 A > 20 A limit) — triggers current_out_of_range'
    results.append(r)

    # --- Scenario 3: temperature_jump ---
    def inj_temp_jump(v, t, i, dv, dt, di, idx):
        return v, t + 15.0, i, dv, 15.0, di
    r = run_scenario('temperature_jump', [dict(s) for s in base_samples], inj_temp_jump,
                     cfg, scaler, weights, feature_names)
    r['notes'] = 'temperature delta set to 15 C (> threshold 9.3 C) — triggers abrupt_temperature'
    results.append(r)

    # --- Scenario 4: voltage_flatline ---
    def inj_voltage_flatline(v, t, i, dv, dt, di, idx):
        return 3.95, t, i, 0.0, dt, di
    r = run_scenario('voltage_flatline', [dict(s) for s in base_samples], inj_voltage_flatline,
                     cfg, scaler, weights, feature_names)
    r['notes'] = 'voltage stuck at 3.95 V, delta=0 — no direct anomaly rule for flatline; tests no-detection case'
    results.append(r)

    # --- Scenario 5: current_dropout ---
    def inj_current_dropout(v, t, i, dv, dt, di, idx):
        return v, t, 0.5, dv, dt, 0.5 - i
    r = run_scenario('current_dropout', [dict(s) for s in base_samples], inj_current_dropout,
                     cfg, scaler, weights, feature_names)
    r['notes'] = 'current drops to 0.5 mA — large negative delta_current > threshold'
    results.append(r)

    # --- Scenario 6: noise_burst ---
    import math as _math
    def inj_noise_burst(v, t, i, dv, dt, di, idx):
        noise_v = 0.3 * _math.sin(idx * 2.1)
        noise_i = 200.0 * _math.cos(idx * 1.7)
        noise_t = 12.0 * _math.sin(idx * 0.9)
        return v + noise_v, t + noise_t, i + noise_i, dv + noise_v, dt + noise_t, di + noise_i
    r = run_scenario('noise_burst', [dict(s) for s in base_samples], inj_noise_burst,
                     cfg, scaler, weights, feature_names)
    r['notes'] = 'deterministic pseudo-noise on all signals — may trigger multiple rules'
    results.append(r)

    # --- Scenario 7: soc_temporal_incoherence ---
    # This scenario injects a large voltage jump that forces a large SOC change
    def inj_soc_incoherence(v, t, i, dv, dt, di, idx):
        big_dv = 0.8 if idx % 2 == 0 else -0.8
        return v + big_dv * 0.3, t, i, big_dv, dt, di
    r = run_scenario('soc_temporal_incoherence', [dict(s) for s in base_samples], inj_soc_incoherence,
                     cfg, scaler, weights, feature_names)
    r['notes'] = 'large alternating delta_voltage (0.8 V) — triggers abrupt_voltage and soc_jump if SOC changes rapidly'
    results.append(r)

    # --- Scenario 8: domain_shift_current_scale ---
    # Oxford uses ~720 mA constant; IoT uses 50-326 mA. Simulate Oxford-like scale
    OXFORD_FACTOR = 812.857
    def inj_domain_shift(v, t, i, dv, dt, di, idx):
        i_shifted = i * (OXFORD_FACTOR / 100.0)
        di_shifted = di * (OXFORD_FACTOR / 100.0)
        return v, t, i_shifted, dv, dt, di_shifted
    r = run_scenario('domain_shift_current_scale', [dict(s) for s in base_samples], inj_domain_shift,
                     cfg, scaler, weights, feature_names)
    r['notes'] = ('Oxford domain shift: current scaled by ~8x to simulate Oxford-scale values. '
                  'May trigger current_out_of_range if i_shifted > 20000 mA. '
                  'Domain shift factor: 812.857x (measured in V6).')
    results.append(r)

    # --- Write results ---
    out_path = os.path.join(OUT_DIR, 'v7_fault_injection_results.csv')
    fieldnames = ['scenario', 'samples', 'injected_samples', 'anomaly_flags_in_fault_zone',
                  'flag_rate', 'detection_delay_samples', 'false_positives_outside_fault',
                  'false_positive_context', 'status', 'notes']
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print('[OK] Wrote: {} ({} scenarios)'.format(out_path, len(results)))

    # --- Summary ---
    n_detected = sum(1 for r in results if r['status'] == 'DETECTED')
    n_missed = sum(1 for r in results if r['status'] == 'MISSED')
    print('[V7A-FAULT] Detected: {}/{} | Missed: {}/{}'.format(
        n_detected, len(results), n_missed, len(results)))
    print('[NOTE] All scenarios are SYNTHETIC — not validated on real fault data.')
    print('[NOTE] Thresholds from anomaly_config_v4.json (offline V4 calibration).')
    for r in results:
        print('  [{:>8}] {:<35} flag_rate={:.2f}'.format(
            r['status'], r['scenario'], r['flag_rate']))


if __name__ == '__main__':
    main()
