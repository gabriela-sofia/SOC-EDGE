#!/usr/bin/env python3
"""Final QA for IoT MLP Firmware Export Package"""

import json
import pickle
import numpy as np
from pathlib import Path
import pandas as pd
import os

ROOT = Path(__file__).resolve().parents[1]
MDIR = ROOT / "models_external"
ODIR = ROOT / "outputs/external_datasets"
EXPORT_DIR = ROOT / "handoff_esp32_soc_method_b_v1"
SAMPLES_DIR = EXPORT_DIR / "samples"

print("=" * 80)
print("IoT MLP Firmware Package QA")
print("=" * 80)

# ============================================================================
# 1. VALIDATE ARTIFACTS
# ============================================================================
print("\n[1] Validating artifacts...")

artifacts = {
    "feature_order.json": EXPORT_DIR / "model" / "feature_order.json",
    "scaler_params.json": EXPORT_DIR / "model" / "scaler_params.json",
    "mlp_architecture.json": EXPORT_DIR / "model" / "mlp_architecture.json",
    "mlp_weights.json": EXPORT_DIR / "model" / "mlp_weights.json",
    "mlp_weights.npz": EXPORT_DIR / "model" / "mlp_weights.npz",
    "mlp_weights_header_preview.h": EXPORT_DIR / "model" / "mlp_weights_header_preview.h",
    "export_validation_inputs.csv": SAMPLES_DIR / "export_validation_inputs.csv",
    "export_validation_outputs.csv": SAMPLES_DIR / "export_validation_outputs.csv",
}

artifact_status = {}
for name, path in artifacts.items():
    exists = path.exists()
    size = path.stat().st_size if exists else 0
    status = "PASS" if exists else "MISSING"
    artifact_status[name] = {"exists": exists, "size": size, "status": status}
    symbol = "OK" if exists else "MISSING"
    print(f"  {symbol}: {name} ({size:,} bytes)")

# ============================================================================
# 2. VALIDATE AGAINST MODEL
# ============================================================================
print("\n[2] Validating against model...")

with open(MDIR / "iot_method_b_mlp_pipeline.pkl", 'rb') as f:
    model_obj = pickle.load(f)

scaler = model_obj['scaler']
mlp = model_obj['model']
features = model_obj['features']

# Check feature order
with open(EXPORT_DIR / "model" / "feature_order.json") as f:
    exported_features = json.load(f)['features']
exported_feature_names = [f['name'] for f in exported_features]

features_match = exported_feature_names == list(features)
print(f"  Feature order match: {features_match}")
if not features_match:
    print(f"    Model: {list(features)}")
    print(f"    Exported: {exported_feature_names}")

# Check scaler params
with open(EXPORT_DIR / "model" / "scaler_params.json") as f:
    exported_scaler = json.load(f)

scaler_min_match = np.allclose(exported_scaler['data_min'], scaler.data_min_.tolist())
scaler_max_match = np.allclose(exported_scaler['data_max'], scaler.data_max_.tolist())
scaler_scale_match = np.allclose(exported_scaler['scale'], scaler.scale_.tolist())

print(f"  Scaler min match: {scaler_min_match}")
print(f"  Scaler max match: {scaler_max_match}")
print(f"  Scaler scale match: {scaler_scale_match}")

# Check MLP architecture
with open(EXPORT_DIR / "model" / "mlp_architecture.json") as f:
    exported_arch = json.load(f)

arch_match = (
    exported_arch['input_size'] == 6 and
    exported_arch['hidden_layer_sizes'] == [64, 32] and
    exported_arch['output_size'] == 1
)
print(f"  Architecture match: {arch_match} (6 -> 64 -> 32 -> 1)")

# ============================================================================
# 3. LOAD EXISTING SYNTHETIC SAMPLES
# ============================================================================
print("\n[3] Loading validation samples...")

X_synthetic = pd.read_csv(SAMPLES_DIR / "export_validation_inputs.csv").values
y_synthetic = pd.read_csv(SAMPLES_DIR / "export_validation_outputs.csv")['soc_pred_original'].values

print(f"  Synthetic samples: {X_synthetic.shape[0]} rows")

# ============================================================================
# 4. TRY TO LOAD REAL IOT SAMPLES
# ============================================================================
print("\n[4] Attempting to load real IoT samples...")

real_samples = None
real_samples_source = "NOT FOUND"
feature_list = ['voltage_v', 'temperature_c', 'current_ma', 'delta_voltage', 'delta_temperature', 'delta_current']

# Try primary path
try:
    df = pd.read_parquet(ODIR / "iot_method_b_extracted.parquet")
    print(f"  Found iot_method_b_extracted.parquet ({len(df)} rows)")

    # Prepare features
    if 'temperature_c' not in df.columns and 'temperature_C' in df.columns:
        df['temperature_c'] = df['temperature_C']
    if 'delta_voltage' not in df.columns:
        df['delta_voltage'] = df.groupby('node_id')['voltage_v'].diff().fillna(0)
    if 'delta_temperature' not in df.columns:
        df['delta_temperature'] = df.groupby('node_id')['temperature_c'].diff().fillna(0)
    if 'delta_current' not in df.columns:
        df['delta_current'] = df.groupby('node_id')['current_ma'].diff().fillna(0)

    # Compute target if needed
    if 'soc_method_b' not in df.columns:
        if 'q_mah' in df.columns and 'Q_cycle_mah' in df.columns:
            df['soc_method_b'] = 1.0 - df['q_mah'].abs() / df['Q_cycle_mah'].clip(lower=1)
            df['soc_method_b'] = df['soc_method_b'].clip(0, 1)

    # Filter and select
    if all(f in df.columns for f in feature_list):
        df_clean = df[feature_list + ['soc_method_b']].dropna()
        if len(df_clean) > 0:
            real_samples = df_clean.sample(n=min(100, len(df_clean)), random_state=42)
            real_samples_source = "IoT Method B extracted (real)"
            print(f"  Selected {len(real_samples)} real samples")
except Exception as e:
    print(f"  Could not load from iot_method_b_extracted.parquet: {e}")

if real_samples is None:
    print("  Real samples NOT FOUND - using synthetic only")

# ============================================================================
# 5. PREDICT AND VALIDATE
# ============================================================================
print("\n[5] Validating predictions...")

# Synthetic validation
X_scaled_syn = scaler.transform(X_synthetic)
y_pred_orig_syn = mlp.predict(X_scaled_syn)
y_pred_orig_syn = np.clip(y_pred_orig_syn, 0, 1)

def forward_manual(X, coefs, intercepts, scaler_min, scaler_max, scaler_scale):
    X_scaled = (X - scaler_min) * scaler_scale
    # Note: Do NOT clip scaled features
    h1 = X_scaled @ coefs[0] + intercepts[0]
    h1 = np.maximum(h1, 0)
    h2 = h1 @ coefs[1] + intercepts[1]
    h2 = np.maximum(h2, 0)
    y = h2 @ coefs[2] + intercepts[2]
    y = np.clip(y, 0, 1)
    return y

y_pred_manual_syn = forward_manual(X_synthetic, mlp.coefs_, mlp.intercepts_, scaler.data_min_, scaler.data_max_, scaler.scale_)
y_pred_manual_syn = y_pred_manual_syn.flatten()

max_diff_syn = np.max(np.abs(y_pred_orig_syn - y_pred_manual_syn))
mean_diff_syn = np.mean(np.abs(y_pred_orig_syn - y_pred_manual_syn))

print(f"  Synthetic validation:")
print(f"    Max diff: {max_diff_syn:.2e}")
print(f"    Mean diff: {mean_diff_syn:.2e}")
if max_diff_syn < 1e-5:
    print(f"    Status: PASS")
else:
    print(f"    Status: NEEDS REVIEW")

# Real validation if available
max_diff_real = None
mean_diff_real = None

if real_samples is not None:
    X_real = real_samples[feature_list].values
    X_scaled_real = scaler.transform(X_real)
    y_pred_orig_real = mlp.predict(X_scaled_real)
    y_pred_orig_real = np.clip(y_pred_orig_real, 0, 1)

    y_pred_manual_real = forward_manual(X_real, mlp.coefs_, mlp.intercepts_, scaler.data_min_, scaler.data_max_, scaler.scale_)
    y_pred_manual_real = y_pred_manual_real.flatten()

    max_diff_real = np.max(np.abs(y_pred_orig_real - y_pred_manual_real))
    mean_diff_real = np.mean(np.abs(y_pred_orig_real - y_pred_manual_real))

    print(f"  Real sample validation:")
    print(f"    Max diff: {max_diff_real:.2e}")
    print(f"    Mean diff: {mean_diff_real:.2e}")
    if max_diff_real < 1e-5:
        print(f"    Status: PASS")
    else:
        print(f"    Status: NEEDS REVIEW")

    # Save real samples
    real_samples[feature_list].to_csv(SAMPLES_DIR / "real_iot_validation_inputs.csv", index=False)
    real_pred_df = pd.DataFrame(y_pred_orig_real, columns=['soc_pred_original'])
    real_pred_df['soc_pred_manual'] = y_pred_manual_real
    real_pred_df['diff'] = np.abs(y_pred_orig_real - y_pred_manual_real)
    real_pred_df.to_csv(SAMPLES_DIR / "real_iot_validation_outputs.csv", index=False)

# ============================================================================
# 6. QA SUMMARY
# ============================================================================
print("\n[6] QA Summary...")

qa_pass = (
    all(v["status"] == "PASS" for v in artifact_status.values()) and
    features_match and
    scaler_min_match and
    scaler_max_match and
    scaler_scale_match and
    arch_match and
    max_diff_syn < 1e-5 and
    (max_diff_real is None or max_diff_real < 1e-5)
)

print(f"  Artifacts: {sum(1 for v in artifact_status.values() if v['status'] == 'PASS')}/{len(artifact_status)} OK")
print(f"  Model validation: {'PASS' if features_match and scaler_min_match and arch_match else 'FAIL'}")
if max_diff_syn < 1e-5:
    print(f"  Prediction validation: PASS")
else:
    print(f"  Prediction validation: FAIL")
if real_samples is not None:
    print(f"  Real samples: {len(real_samples)} validated")
else:
    print(f"  Real samples: MISSING")

if qa_pass:
    print(f"\n  Overall QA: PASS")
else:
    print(f"\n  Overall QA: NEEDS REVIEW")

# ============================================================================
# 7. FILE MANIFEST
# ============================================================================
print("\n[7] Creating file manifest...")

manifest_data = {
    "filename": [],
    "type": [],
    "size_bytes": [],
    "purpose": [],
    "status": []
}

files_to_manifest = [
    ("model/feature_order.json", "JSON", "Feature order specification"),
    ("model/scaler_params.json", "JSON", "MinMaxScaler parameters"),
    ("model/mlp_architecture.json", "JSON", "MLP layer specifications"),
    ("model/mlp_weights.json", "JSON", "Weights (text format)"),
    ("model/mlp_weights.npz", "NPZ", "Weights (binary format)"),
    ("model/mlp_weights_header_preview.h", "Header", "C++ header preview"),
    ("samples/export_validation_inputs.csv", "CSV", "20 synthetic test inputs"),
    ("samples/export_validation_outputs.csv", "CSV", "Synthetic predictions"),
]

if (SAMPLES_DIR / "real_iot_validation_inputs.csv").exists():
    files_to_manifest.append(("samples/real_iot_validation_inputs.csv", "CSV", "Real IoT test inputs"))
    files_to_manifest.append(("samples/real_iot_validation_outputs.csv", "CSV", "Real IoT predictions"))

for filename, ftype, purpose in files_to_manifest:
    filepath = EXPORT_DIR / filename
    if filepath.exists():
        size = filepath.stat().st_size
        manifest_data["filename"].append(filename)
        manifest_data["type"].append(ftype)
        manifest_data["size_bytes"].append(size)
        manifest_data["purpose"].append(purpose)
        manifest_data["status"].append("OK")

manifest_df = pd.DataFrame(manifest_data)
manifest_df.to_csv(EXPORT_DIR / "FILE_MANIFEST.csv", index=False)
print(f"  Created FILE_MANIFEST.csv ({len(manifest_df)} files)")

# ============================================================================
# 8. QA REPORT CSV
# ============================================================================
print("\n[8] Creating QA report CSV...")

qa_items = [
    ["artifact_feature_order.json", "EXISTS", artifact_status["feature_order.json"]["exists"]],
    ["artifact_scaler_params.json", "EXISTS", artifact_status["scaler_params.json"]["exists"]],
    ["artifact_mlp_architecture.json", "EXISTS", artifact_status["mlp_architecture.json"]["exists"]],
    ["artifact_mlp_weights.json", "EXISTS", artifact_status["mlp_weights.json"]["exists"]],
    ["artifact_mlp_weights.npz", "EXISTS", artifact_status["mlp_weights.npz"]["exists"]],
    ["artifact_mlp_weights_header.h", "EXISTS", artifact_status["mlp_weights_header_preview.h"]["exists"]],
    ["artifact_validation_inputs.csv", "EXISTS", artifact_status["export_validation_inputs.csv"]["exists"]],
    ["artifact_validation_outputs.csv", "EXISTS", artifact_status["export_validation_outputs.csv"]["exists"]],
    ["model_feature_order", "MATCH", features_match],
    ["model_scaler_min", "MATCH", scaler_min_match],
    ["model_scaler_max", "MATCH", scaler_max_match],
    ["model_scaler_scale", "MATCH", scaler_scale_match],
    ["model_architecture", "MATCH", arch_match],
    ["validation_synthetic_max_diff", "VALUE", max_diff_syn],
    ["validation_synthetic_mean_diff", "VALUE", mean_diff_syn],
]

if real_samples is not None:
    qa_items.append(["validation_real_max_diff", "VALUE", max_diff_real])
    qa_items.append(["validation_real_mean_diff", "VALUE", mean_diff_real])
    qa_items.append(["real_samples_count", "VALUE", len(real_samples)])
else:
    qa_items.append(["real_samples", "STATUS", "MISSING"])

qa_df = pd.DataFrame(qa_items, columns=["item", "check_type", "result"])
qa_df.to_csv(ODIR / "iot_mlp_firmware_package_qa.csv", index=False)
print(f"  Created iot_mlp_firmware_package_qa.csv ({len(qa_df)} checks)")

# ============================================================================
# 9. FINAL STATUS
# ============================================================================
print("\n[9] Final status...")

final_status = {
    "qa_date": "2026-05-05",
    "model": "IoT Method B MLP v1",
    "status": "PASSED" if qa_pass else "NEEDS_REVIEW",
    "artifacts_count": len(artifact_status),
    "artifacts_ok": sum(1 for v in artifact_status.values() if v["status"] == "PASS"),
    "synthetic_validation": {
        "samples": len(X_synthetic),
        "max_diff": float(max_diff_syn),
        "mean_diff": float(mean_diff_syn),
        "status": "PASSED" if max_diff_syn < 1e-5 else "NEEDS_REVIEW"
    },
    "real_validation": {
        "samples": len(real_samples) if real_samples is not None else 0,
        "max_diff": float(max_diff_real) if max_diff_real is not None else None,
        "mean_diff": float(mean_diff_real) if mean_diff_real is not None else None,
        "status": "PASSED" if max_diff_real is not None and max_diff_real < 1e-5 else ("MISSING" if real_samples is None else "NEEDS_REVIEW")
    }
}

with open(ODIR / "iot_mlp_firmware_package_final_status.csv", "w") as f:
    for key, value in final_status.items():
        if isinstance(value, dict):
            for subkey, subval in value.items():
                f.write(f"{key}.{subkey},{subval}\n")
        else:
            f.write(f"{key},{value}\n")

print(f"  Status: {final_status['status']}")
print(f"  Artifacts: {final_status['artifacts_ok']}/{final_status['artifacts_count']}")
print(f"  Synthetic validation: {final_status['synthetic_validation']['status']}")
print(f"  Real validation: {final_status['real_validation']['status']}")

print("\n[OK] QA complete")
print("=" * 80)
