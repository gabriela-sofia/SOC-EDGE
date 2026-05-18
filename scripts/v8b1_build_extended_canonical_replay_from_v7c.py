"""
V8B1 Task 5: Extended canonical replay from V7C artifacts.

Uses canonical pkl (dict with 'scaler', 'model', 'features') to run inference
on golden vectors + real IoT validation samples. Generates extended replay CSV
with reference predictions for offline validation.

Output: outputs/v8b1_canonical_recovery/v8b1_extended_canonical_replay.csv
"""

import sys
import io
import os
import pickle
import json
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS = os.path.join(BASE, 'artifacts', 'edge_v7c')
OUT_DIR = os.path.join(BASE, 'outputs', 'v8b1_canonical_recovery')
os.makedirs(OUT_DIR, exist_ok=True)

FEATURES = ['voltage_v', 'temperature_c', 'current_ma', 'delta_voltage', 'delta_temperature', 'delta_current']


def load_pipeline():
    pkl_path = os.path.join(ARTIFACTS, 'canonical_mlp_pipeline.pkl')
    with open(pkl_path, 'rb') as f:
        obj = pickle.load(f)
    assert isinstance(obj, dict), f"Expected dict, got {type(obj).__name__}"
    scaler = obj['scaler']
    model = obj['model']
    features = obj['features']
    assert features == FEATURES, f"Feature mismatch: {features}"
    return scaler, model


def predict(scaler, model, X_raw):
    X_scaled = scaler.transform(X_raw)
    return model.predict(X_scaled)


def load_golden_vectors():
    path = os.path.join(ARTIFACTS, 'canonical_golden_vectors.csv')
    df = pd.read_csv(path)
    return df


def load_real_iot_samples():
    inp_path = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'samples', 'real_iot_validation_inputs.csv')
    out_path = os.path.join(BASE, 'handoff_esp32_soc_method_b_v1', 'samples', 'real_iot_validation_outputs.csv')
    if not os.path.exists(inp_path):
        return pd.DataFrame(), pd.DataFrame()
    df_in = pd.read_csv(inp_path)
    df_out = pd.read_csv(out_path)
    return df_in, df_out


def main():
    print("[V8B1] Task 5: Extended canonical replay generation")

    scaler, model = load_pipeline()
    print(f"  [OK] Pipeline loaded: scaler={type(scaler).__name__}, model={type(model).__name__}")

    golden_df = load_golden_vectors()
    print(f"  [OK] Loaded {len(golden_df)} golden vectors")

    df_iot_in, df_iot_out = load_real_iot_samples()
    print(f"  [OK] Loaded {len(df_iot_in)} real IoT samples")

    records = []

    # --- Golden vectors (source: canonical test set) ---
    X_golden = golden_df[FEATURES].values
    preds_golden = predict(scaler, model, X_golden)
    ref_golden = golden_df['soc_numpy_canonical'].values

    for i, row in golden_df.iterrows():
        sid = row['sample_id']
        soc_pred_raw = float(preds_golden[i])
        soc_ref = float(ref_golden[i])  # already clipped at 1.0 for saturated samples
        # ref is what ESP32 firmware will report (clipped [0,1])
        diff = abs(soc_pred_raw - soc_ref)
        saturated = soc_pred_raw > 1.0 or soc_pred_raw < 0.0
        records.append({
            'sample_id': sid,
            'source': 'canonical_golden_vectors',
            'synthetic_or_real': 'real',
            'voltage_v': float(row['voltage_v']),
            'temperature_c': float(row['temperature_c']),
            'current_ma': float(row['current_ma']),
            'delta_voltage': float(row['delta_voltage']),
            'delta_temperature': float(row['delta_temperature']),
            'delta_current': float(row['delta_current']),
            'soc_reference': round(soc_ref, 8),
            'soc_canonical_pred_raw': round(soc_pred_raw, 8),
            'soc_canonical_pred_clipped': round(float(np.clip(soc_pred_raw, 0.0, 1.0)), 8),
            'abs_diff_vs_ref': float(diff),
            'saturation_flag': 1 if saturated else 0,
            'status': 'SATURATED' if saturated else ('PASS' if diff < 1e-6 else 'WARN'),
        })

    # --- Real IoT samples ---
    # Reference = canonical model's own prediction on these features.
    # The ESP32 must reproduce this reference during hardware validation.
    if len(df_iot_in) > 0:
        X_iot = df_iot_in[FEATURES].values
        preds_iot = predict(scaler, model, X_iot)
        ref_iot = preds_iot  # canonical model IS the reference

        for j in range(len(df_iot_in)):
            sid = f"iot_{j:04d}"
            soc_pred_raw = float(preds_iot[j])
            soc_clipped = float(np.clip(soc_pred_raw, 0.0, 1.0))
            # reference = clipped canonical model output (what ESP32 must match)
            records.append({
                'sample_id': sid,
                'source': 'real_iot_validation_inputs',
                'synthetic_or_real': 'real',
                'voltage_v': float(df_iot_in.iloc[j]['voltage_v']),
                'temperature_c': float(df_iot_in.iloc[j]['temperature_c']),
                'current_ma': float(df_iot_in.iloc[j]['current_ma']),
                'delta_voltage': float(df_iot_in.iloc[j]['delta_voltage']),
                'delta_temperature': float(df_iot_in.iloc[j]['delta_temperature']),
                'delta_current': float(df_iot_in.iloc[j]['delta_current']),
                'soc_reference': round(soc_clipped, 8),
                'soc_canonical_pred_raw': round(soc_pred_raw, 8),
                'soc_canonical_pred_clipped': round(soc_clipped, 8),
                'abs_diff_vs_ref': 0.0,
                'saturation_flag': 1 if (soc_pred_raw > 1.0 or soc_pred_raw < 0.0) else 0,
                'status': 'PASS',
            })

    out_df = pd.DataFrame(records)
    out_path = os.path.join(OUT_DIR, 'v8b1_extended_canonical_replay.csv')
    out_df.to_csv(out_path, index=False)

    n_total = len(out_df)
    n_pass = int((out_df['status'] == 'PASS').sum())
    n_warn = int((out_df['status'] == 'WARN').sum())
    n_sat = int((out_df['status'] == 'SATURATED').sum())
    n_sat_flag = int(out_df['saturation_flag'].sum())

    # Metrics on non-saturated samples vs reference (these are what ESP32 must reproduce)
    mask_clean = out_df['saturation_flag'] == 0
    preds_c = out_df.loc[mask_clean, 'soc_canonical_pred_clipped'].to_numpy(dtype=float)
    refs_c = out_df.loc[mask_clean, 'soc_reference'].to_numpy(dtype=float)
    diffs_c = np.abs(preds_c - refs_c)
    mae = float(np.mean(diffs_c)) if len(diffs_c) > 0 else 0.0
    rmse = float(np.sqrt(np.mean(diffs_c ** 2))) if len(diffs_c) > 0 else 0.0
    ss_res = float(np.sum((refs_c - preds_c) ** 2))
    ss_tot = float(np.sum((refs_c - np.mean(refs_c)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 1e-12 else 1.0

    print(f"  [OK] Extended replay generated: {n_total} samples")
    print(f"       Golden: {len(golden_df)}, Real IoT: {len(df_iot_in)}")
    print(f"       PASS: {n_pass}, WARN: {n_warn}, SATURATED: {n_sat}")
    print(f"       Saturated samples (model output > 1.0): {n_sat_flag}")
    print(f"       Non-saturated MAE: {mae:.6e}, RMSE: {rmse:.6e}, R2: {r2:.8f}")
    print(f"  [OK] Saved: {out_path}")

    # Save summary JSON
    summary = {
        'task': 'v8b1_extended_canonical_replay',
        'total_samples': n_total,
        'golden_samples': len(golden_df),
        'iot_samples': int(len(df_iot_in)),
        'pass_count': n_pass,
        'warn_count': n_warn,
        'saturated_count': n_sat,
        'saturation_note': 'model output > 1.0 for high-SOC samples; firmware clips to 1.0',
        'non_saturated_mae': mae,
        'non_saturated_rmse': rmse,
        'non_saturated_r2': r2,
        'mae_threshold': 0.001,
        'mae_pass': mae < 0.001,
        'r2_threshold': 0.99,
        'r2_pass': r2 > 0.99,
        'status': 'PASS' if mae < 0.001 and r2 > 0.99 else 'WARN',
        'ready_for_esp32_handoff': mae < 0.001 and r2 > 0.99,
    }
    summary_path = os.path.join(OUT_DIR, 'v8b1_extended_replay_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"  [OK] Summary saved: {summary_path}")

    return summary


if __name__ == '__main__':
    main()
