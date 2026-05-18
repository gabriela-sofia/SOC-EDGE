"""
V8B2 Package Artifact Generation Script.

Generates all data artifacts for the V8B2 canonical handoff package:
- Replay CSVs (golden, extended, saturation, manifest)
- Anomaly scenarios
- Model manifest
- Lock manifest

Does NOT generate firmware, validator, or documentation (those are separate files).
"""

import os
import json
import shutil
import pickle
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(BASE, 'artifacts', 'edge_v7c')
PKG = os.path.join(BASE, 'handoff_esp32_v8b2_canonical')
OUT = os.path.join(BASE, 'outputs', 'v8b2_handoff_package')
V8B1 = os.path.join(BASE, 'outputs', 'v8b1_canonical_recovery')

FEATURES = ['voltage_v', 'temperature_c', 'current_ma', 'delta_voltage', 'delta_temperature', 'delta_current']

SERIAL_SCHEMA = 'sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status'

print('[V8B2] Artifact generation starting...')


# --- Load canonical pipeline ---
with open(os.path.join(ART, 'canonical_mlp_pipeline.pkl'), 'rb') as f:
    pipeline = pickle.load(f)
scaler = pipeline['scaler']
model = pipeline['model']


def predict_canonical(X_raw):
    X_sc = scaler.transform(np.array(X_raw).reshape(-1, 6))
    preds_raw = model.predict(X_sc)
    preds_clipped = np.clip(preds_raw, 0.0, 1.0)
    return preds_raw, preds_clipped


# ============================================================
# T2: Copy canonical artifacts + generate MODEL_MANIFEST
# ============================================================
print('[V8B2] T2: Copying canonical artifacts to model/')
model_dir = os.path.join(PKG, 'model')

artifacts_to_copy = [
    ('canonical_feature_order.json', 'canonical_feature_order_v7c.json'),
    ('canonical_scaler_params.json', 'canonical_scaler_params_v7c.json'),
    ('canonical_golden_vectors.csv', 'canonical_golden_vectors_v7c.csv'),
    ('canonical_expected_serial_output.csv', 'canonical_expected_serial_output_v7c.csv'),
    ('canonical_model_weights.json', 'canonical_model_weights_v7c.json'),
]
for src_name, dst_name in artifacts_to_copy:
    src = os.path.join(ART, src_name)
    dst = os.path.join(model_dir, dst_name)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f'  [OK] Copied: {src_name} -> {dst_name}')
    else:
        print(f'  [WARN] Missing: {src_name}')

# Load scaler params for manifest
with open(os.path.join(ART, 'canonical_scaler_params.json')) as f:
    sc_params = json.load(f)

manifest_md = f"""# Model Manifest V8B2

**Package:** V8B2 Canonical Handoff
**Date:** 2026-05-16
**Status:** OFFLINE_APPROVED -- ESP32 VALIDATION PENDING

---

## Model Identification

| Field | Value |
|-------|-------|
| Model version | V7C Canonical |
| Training target | soc_method_b |
| Architecture | Input(6) -> Dense(64, ReLU) -> Dense(32, ReLU) -> Dense(1, linear) |
| Parameters | 2561 |
| R2 (offline) | 0.7937 (approved threshold met) |
| CANONICAL_FROZEN | 2026-05-15 |

## Features (CANONICAL ORDER -- MANDATORY)

| Index | Name | Unit | Notes |
|-------|------|------|-------|
| 0 | voltage_v | V | Cell terminal voltage |
| 1 | temperature_c | C | Battery temperature |
| 2 | current_ma | mA | **CRITICAL: mA not A. Firmware must feed mA.** |
| 3 | delta_voltage | V | voltage_v[t] - voltage_v[t-1] |
| 4 | delta_temperature | C | temperature_c[t] - temperature_c[t-1] |
| 5 | delta_current | mA | current_ma[t] - current_ma[t-1] in mA |

## MinMax Scaler (EXACT V7C BOUNDS)

```
data_min = [{', '.join(f'{v:.8f}' for v in sc_params['data_min'])}]
data_max = [{', '.join(f'{v:.8f}' for v in sc_params['data_max'])}]
scale    = [{', '.join(f'{v:.8f}' for v in sc_params['scale'])}]

x_scaled[i] = (x[i] - data_min[i]) * scale[i]
```

## Clipping Rule

The model (sklearn MLPRegressor, linear output) can produce values outside [0, 1]
for out-of-distribution inputs. **Firmware MUST clip the output:**

```c
soc_final = fmaxf(0.0f, fminf(1.0f, raw_model_output));
```

6 samples in the 120-sample extended replay are known to saturate.
3 produce raw output > 1.0 (high-SOC extrapolation).
3 produce raw output < 0.0 (low-SOC extrapolation).

## Inference Path

```
Input (6 floats, mA units)
  -> MinMax scale
  -> Dense(64, ReLU)
  -> Dense(32, ReLU)
  -> Dense(1, linear)
  -> Clip to [0.0, 1.0]
  -> soc_final
```

## Validation Status

| Scope | Status |
|-------|--------|
| Offline Python (Phase 3C) | VALIDATED -- 96/96 tests pass |
| ESP32 V7B/legacy (V8A) | VALIDATED -- MAE=2.4e-7, 20 samples |
| ESP32 V7C canonical | PENDING -- this package prepares for it |
| Field operation | NOT TESTED |
| Anomaly detection (embedded) | NOT IMPLEMENTED |

## Limitations

- V7C has NOT yet been validated on ESP32 hardware.
- Scaler must use EXACT floating-point bounds above (no rounding).
- Model degrades outside training range (voltage < 3.87V, current > 326mA).
- Temperature below 9.41C or above 40.19C is extrapolation.
- Anomaly detection rules (Phase 1) are heuristic thresholds, not ML-based.

---

*Status: OFFLINE_APPROVED -- ESP32 VALIDATION PENDING*
"""
with open(os.path.join(model_dir, 'MODEL_MANIFEST_V8B2.md'), 'w', encoding='utf-8') as f:
    f.write(manifest_md)
print('  [OK] Created: MODEL_MANIFEST_V8B2.md')


# ============================================================
# T4: Copy C header to firmware/
# ============================================================
print('[V8B2] T4: Copying C header to firmware/')
firmware_dir = os.path.join(PKG, 'firmware')
h_src = os.path.join(ART, 'canonical_model_weights_preview.h')
h_dst = os.path.join(firmware_dir, 'canonical_model_weights_v8b2.h')

with open(h_src, 'r', encoding='utf-8', errors='replace') as f:
    h_content = f.read()

# Replace header guard and add V8B2 annotation
h_content = h_content.replace(
    '/* V7C Canonical MLP Weights',
    '/* V7C Canonical MLP Weights -- V8B2 Handoff Package'
).replace(
    '#ifndef IOT_MLP_CANONICAL_WEIGHTS_H',
    '#ifndef CANONICAL_MODEL_WEIGHTS_V8B2_H'
).replace(
    '#define IOT_MLP_CANONICAL_WEIGHTS_H',
    '#define CANONICAL_MODEL_WEIGHTS_V8B2_H'
).replace(
    '#endif /* IOT_MLP_CANONICAL_WEIGHTS_H */',
    '#endif /* CANONICAL_MODEL_WEIGHTS_V8B2_H */'
)

with open(h_dst, 'w', encoding='utf-8') as f:
    f.write(h_content)
print(f'  [OK] Created: canonical_model_weights_v8b2.h ({len(h_content)} chars)')


# ============================================================
# T5: Generate replay CSVs
# ============================================================
print('[V8B2] T5: Generating replay CSVs')
replay_dir = os.path.join(PKG, 'replay')

# Load V8B1 extended replay as base
v8b1_replay = pd.read_csv(os.path.join(V8B1, 'v8b1_extended_canonical_replay.csv'))

# --- 5a: Golden vectors V8B2 ---
golden_src = pd.read_csv(os.path.join(ART, 'canonical_golden_vectors.csv'))
golden_ref = pd.read_csv(os.path.join(ART, 'canonical_expected_serial_output.csv'))

X_golden = golden_src[FEATURES].values
preds_raw_g, preds_clipped_g = predict_canonical(X_golden)

golden_rows = []
for i, row in golden_src.iterrows():
    sid = row['sample_id']
    ref_row = golden_ref[golden_ref['sample_id'] == sid].iloc[0] if len(golden_ref[golden_ref['sample_id'] == sid]) > 0 else None
    soc_raw = float(preds_raw_g[i])
    soc_clipped = float(preds_clipped_g[i])
    is_sat = soc_raw > 1.0 or soc_raw < 0.0
    golden_rows.append({
        'sample_id': sid,
        'mode': 'GOLDEN',
        'source': 'canonical_golden_vectors_v7c',
        'synthetic_or_real': 'real',
        'voltage_v': float(row['voltage_v']),
        'temperature_c': float(row['temperature_c']),
        'current_ma': float(row['current_ma']),
        'delta_voltage': float(row['delta_voltage']),
        'delta_temperature': float(row['delta_temperature']),
        'delta_current': float(row['delta_current']),
        'soc_raw_model': round(soc_raw, 8),
        'soc_clipped_reference': round(soc_clipped, 8),
        'is_saturated': 1 if is_sat else 0,
        'saturation_reason': 'model_output_above_1' if soc_raw > 1.0 else ('model_output_below_0' if soc_raw < 0.0 else 'NONE'),
    })

golden_df = pd.DataFrame(golden_rows)
golden_df.to_csv(os.path.join(replay_dir, 'canonical_golden_vectors_v8b2.csv'), index=False)
print(f'  [OK] canonical_golden_vectors_v8b2.csv: {len(golden_df)} rows')

# --- 5b: Extended replay V8B2 ---
extended_rows = []
for _, row in v8b1_replay.iterrows():
    extended_rows.append({
        'sample_id': row['sample_id'],
        'mode': 'EXTENDED',
        'source': row['source'],
        'synthetic_or_real': row['synthetic_or_real'],
        'voltage_v': float(row['voltage_v']),
        'temperature_c': float(row['temperature_c']),
        'current_ma': float(row['current_ma']),
        'delta_voltage': float(row['delta_voltage']),
        'delta_temperature': float(row['delta_temperature']),
        'delta_current': float(row['delta_current']),
        'soc_raw_model': float(row['soc_canonical_pred_raw']),
        'soc_clipped_reference': float(row['soc_canonical_pred_clipped']),
        'is_saturated': int(row['saturation_flag']),
        'saturation_reason': (
            'model_output_above_1' if float(row['soc_canonical_pred_raw']) > 1.0
            else ('model_output_below_0' if float(row['soc_canonical_pred_raw']) < 0.0 else 'NONE')
        ),
    })

ext_df = pd.DataFrame(extended_rows)
ext_df.to_csv(os.path.join(replay_dir, 'canonical_extended_replay_v8b2.csv'), index=False)
print(f'  [OK] canonical_extended_replay_v8b2.csv: {len(ext_df)} rows')

# --- 5c: Reference (input + clipped SOC reference only -- what ESP32 must reproduce) ---
ref_rows = []
for _, row in ext_df.iterrows():
    ref_rows.append({
        'sample_id': row['sample_id'],
        'mode': row['mode'],
        'soc_raw_model': row['soc_raw_model'],
        'soc_clipped_reference': row['soc_clipped_reference'],
        'is_saturated': row['is_saturated'],
        'saturation_reason': row['saturation_reason'],
        'source': row['source'],
        'acceptance_criterion': 'soc_clipped_reference',
        'mae_threshold': 0.001,
    })
ref_df = pd.DataFrame(ref_rows)
ref_df.to_csv(os.path.join(replay_dir, 'canonical_extended_reference_v8b2.csv'), index=False)
print(f'  [OK] canonical_extended_reference_v8b2.csv: {len(ref_df)} rows')

# --- 5d: Saturation cases ---
sat_df = ext_df[ext_df['is_saturated'] == 1].copy()
sat_df.to_csv(os.path.join(replay_dir, 'canonical_saturation_cases_v8b2.csv'), index=False)
print(f'  [OK] canonical_saturation_cases_v8b2.csv: {len(sat_df)} rows (saturated)')

# --- 5e: Replay manifest ---
manifest_rows = []
for idx, row in ext_df.iterrows():
    manifest_rows.append({
        'sample_id': row['sample_id'],
        'mode': row['mode'],
        'source': row['source'],
        'synthetic_or_real': row['synthetic_or_real'],
        'soc_clipped_reference': row['soc_clipped_reference'],
        'is_saturated': row['is_saturated'],
        'saturation_reason': row['saturation_reason'],
        'coverage_type': (
            'high_soc_saturation' if row['is_saturated'] and float(row['soc_raw_model']) > 1.0
            else ('low_soc_saturation' if row['is_saturated'] and float(row['soc_raw_model']) < 0.0
                  else ('mid_soc' if float(row['soc_clipped_reference']) > 0.3 and float(row['soc_clipped_reference']) < 0.7
                        else ('low_soc' if float(row['soc_clipped_reference']) <= 0.3 else 'high_soc')))
        ),
    })
manifest_df = pd.DataFrame(manifest_rows)
manifest_df.to_csv(os.path.join(replay_dir, 'canonical_replay_manifest_v8b2.csv'), index=False)
print(f'  [OK] canonical_replay_manifest_v8b2.csv: {len(manifest_df)} rows')


# ============================================================
# T6: Generate anomaly scenarios V8B2
# ============================================================
print('[V8B2] T6: Generating anomaly scenarios')
anomaly_dir = os.path.join(PKG, 'anomaly')

# Reference sample (mid-SOC, normal)
ref_sample = {
    'voltage_v': 4.05, 'temperature_c': 25.0, 'current_ma': 150.0,
    'delta_voltage': 0.0, 'delta_temperature': 0.0, 'delta_current': 0.0
}

# Anomaly scenarios: 10 required
scenarios = [
    # (scenario_id, desc, type, perturbation, embedded_feasible, reference_only, limitation,
    #  anomaly_flag, anomaly_code, severity, voltage, temp, current, dv, dt, di)
    ('ano_001_voltage_spike', 'Sudden +0.5V spike in voltage', 'voltage_out_of_range', '+0.5V', True, False, 'NONE',
     1, 1, 'HIGH', 4.55, 25.0, 150.0, 0.5, 0.0, 0.0),
    ('ano_002_current_spike', 'Sudden +300mA spike in current', 'current_out_of_range', '+300mA', True, False, 'NONE',
     1, 2, 'HIGH', 4.05, 25.0, 450.0, 0.0, 0.0, 300.0),
    ('ano_003_temperature_jump', 'Sudden +20C temperature jump', 'temperature_out_of_range', '+20C', True, False, 'NONE',
     1, 3, 'MEDIUM', 4.05, 55.0, 150.0, 0.0, 20.0, 0.0),
    ('ano_004_voltage_flatline', 'Voltage constant for multiple samples (flatline)', 'voltage_flatline', 'delta_v=0 for 5+ samples', True, False, 'Requires 5-sample window buffer in firmware',
     1, 4, 'MEDIUM', 4.05, 25.0, 150.0, 0.0, 0.0, 0.0),
    ('ano_005_current_dropout', 'Sudden current dropout to near-zero', 'current_dropout', 'current=1mA (below training min)', True, False, 'NONE',
     1, 5, 'HIGH', 4.05, 25.0, 1.0, 0.0, 0.0, -149.0),
    ('ano_006_noise_burst', 'High-frequency noise: large delta_current oscillation', 'abrupt_delta_current', '|delta_i| > 200mA per step', True, False, 'NONE',
     1, 6, 'LOW', 4.05, 25.0, 150.0, 0.0, 0.0, 250.0),
    ('ano_007_soc_temporal_incoherence', 'SOC increases during high discharge (negative coherence)', 'soc_coherence_violation', 'offline reference only', False, True, 'Requires reference lookup table on device; not embedded in Phase 1',
     1, 7, 'MEDIUM', 3.95, 25.0, 300.0, -0.05, 0.0, 50.0),
    ('ano_008_domain_shift_current_scale', 'Current in Amperes instead of mA (10x scale error)', 'domain_shift', 'current=0.15 (should be 150mA; passed as 0.15)', False, True, 'Scale error detectable if current < training_min; depends on value. Mark as REPLAY_WARNING',
     1, 8, 'HIGH', 4.05, 25.0, 0.15, 0.0, 0.0, 0.0),
    ('ano_009_low_voltage_warning', 'Voltage below safe operating minimum (3.8V)', 'voltage_out_of_range', 'voltage=3.75V', True, False, 'NONE',
     1, 9, 'MEDIUM', 3.75, 25.0, 150.0, -0.02, 0.0, 0.0),
    ('ano_010_high_temperature_warning', 'Temperature above safe limit (45C)', 'temperature_out_of_range', 'temperature=48C', True, False, 'NONE',
     1, 10, 'MEDIUM', 4.05, 48.0, 150.0, 0.0, 3.0, 0.0),
]

scenario_rows = []
expected_rows = []
manifest_rows = []

for s in scenarios:
    (sid, desc, atype, perturb, emb_feasible, ref_only, limitation,
     exp_flag, exp_code, severity, volt, temp, curr, dv, dt, di) = s

    # Generate canonical prediction for this sample
    X = np.array([[volt, temp, curr, dv, dt, di]])
    soc_raw, soc_clipped = predict_canonical(X)
    soc_raw = float(soc_raw[0])
    soc_clipped = float(soc_clipped[0])

    scenario_rows.append({
        'scenario_id': sid,
        'description': desc,
        'anomaly_type': atype,
        'perturbation': perturb,
        'voltage_v': volt, 'temperature_c': temp, 'current_ma': curr,
        'delta_voltage': dv, 'delta_temperature': dt, 'delta_current': di,
        'soc_raw_model': round(soc_raw, 6),
        'soc_clipped_reference': round(soc_clipped, 6),
        'expected_anomaly_flag': exp_flag,
        'expected_anomaly_code': exp_code,
        'expected_severity': severity,
        'embedded_feasible': embedded_feasible if isinstance(emb_feasible, str) else ('YES' if emb_feasible else 'NO'),
        'reference_only': 'YES' if ref_only else 'NO',
        'limitation': limitation,
    })

    expected_rows.append({
        'scenario_id': sid,
        'expected_anomaly_flag': exp_flag,
        'expected_anomaly_code': exp_code,
        'expected_severity': severity,
        'embedded_feasible': 'YES' if emb_feasible else 'NO',
        'reference_only': 'YES' if ref_only else 'NO',
    })

    manifest_rows.append({
        'scenario_id': sid,
        'sample_id': f'ano_{exp_code:03d}',
        'mode': 'ANOMALY',
        'anomaly_type': atype,
        'perturbation': perturb,
        'expected_anomaly_flag': exp_flag,
        'expected_anomaly_code': exp_code,
        'expected_severity': severity,
        'embedded_feasible': 'YES' if emb_feasible else 'NO',
        'reference_only': 'YES' if ref_only else 'NO',
        'limitation': limitation,
    })

sc_df = pd.DataFrame(scenario_rows)
sc_df.to_csv(os.path.join(anomaly_dir, 'anomaly_replay_scenarios_v8b2.csv'), index=False)

exp_df = pd.DataFrame(expected_rows)
exp_df.to_csv(os.path.join(anomaly_dir, 'anomaly_expected_flags_v8b2.csv'), index=False)

man_df = pd.DataFrame(manifest_rows)
man_df.to_csv(os.path.join(anomaly_dir, 'anomaly_manifest_v8b2.csv'), index=False)

n_embedded = sum(1 for s in scenarios if s[9])  # embedded_feasible at index 9
print(f'  [OK] anomaly_replay_scenarios_v8b2.csv: {len(sc_df)} scenarios')
print(f'  [OK] anomaly_expected_flags_v8b2.csv: {len(exp_df)} rows')
print(f'  [OK] anomaly_manifest_v8b2.csv: {len(man_df)} rows')
print(f'       Embedded feasible: {n_embedded}/10')


# ============================================================
# T12: Lock manifest
# ============================================================
print('[V8B2] T12: Creating lock manifest')

n_sat = int(ext_df['is_saturated'].sum())
lock = {
    'package_version': 'V8B2',
    'canonical_model_version': 'V7C',
    'package_status': 'PREPARED_PACKAGE_NOT_YET_EXECUTED_ON_ESP32',
    'date_prepared': '2026-05-16',
    'golden_samples': len(golden_df),
    'extended_samples': len(ext_df),
    'saturated_samples': n_sat,
    'anomaly_scenarios': len(sc_df),
    'anomaly_scenarios_embedded_feasible': n_embedded,
    'serial_schema': SERIAL_SCHEMA,
    'serial_schema_fields': 10,
    'modes': ['GOLDEN', 'EXTENDED', 'ANOMALY'],
    'soc_acceptance_mae': 0.001,
    'soc_acceptance_rmse': 0.001,
    'soc_acceptance_r2': 0.99,
    'anomaly_acceptance_recall': 0.90,
    'clipping_rule': 'soc_final = clip(raw_model_output, 0.0, 1.0)',
    'acceptance_reference': 'soc_clipped_reference',
    'features': FEATURES,
    'current_unit': 'mA',
    'esp32_validated': False,
    'v8a_baseline': {
        'model': 'V7B_legacy',
        'samples': 20,
        'mae': 2.4e-7,
        'status': 'VALIDATED'
    },
    'ready_for_future_handoff': True,
    'limitations': [
        'V7C has NOT been validated on ESP32 hardware -- this package prepares for it',
        'Anomaly detection rules are Phase 1 heuristics (thresholds only)',
        'No field-operation validation',
        '6 saturated samples in extended replay -- firmware must clip to [0,1]',
        'ESP32 must use EXACT scaler bounds (no rounding)'
    ]
}

lock_path = os.path.join(OUT, 'v8b2_package_lock_manifest.json')
with open(lock_path, 'w', encoding='utf-8') as f:
    json.dump(lock, f, indent=2)
print(f'  [OK] v8b2_package_lock_manifest.json: {len(lock)} fields')


# ============================================================
# Summary
# ============================================================
print()
print('[V8B2] Generation complete:')
print(f'  Golden samples:      {len(golden_df)}')
print(f'  Extended samples:    {len(ext_df)}')
print(f'  Saturated samples:   {n_sat}')
print(f'  Anomaly scenarios:   {len(sc_df)} (embedded feasible: {n_embedded})')
print(f'  Serial schema:       {SERIAL_SCHEMA}')
print(f'  Acceptance MAE:      < 0.001')
print(f'  Anomaly recall:      >= 0.90 (embedded only)')
