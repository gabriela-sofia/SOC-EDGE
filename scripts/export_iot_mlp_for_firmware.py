#!/usr/bin/env python3
"""Export IoT MLP v1 Model for Firmware Implementation"""

import json
import pickle
import numpy as np
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MDIR = ROOT / "models_external"
ODIR = ROOT / "outputs/external_datasets"
EXPORT_DIR = ROOT / "handoff_esp32_soc_method_b_v1" / "model"
SAMPLES_DIR = ROOT / "handoff_esp32_soc_method_b_v1" / "samples"

EXPORT_DIR.mkdir(parents=True, exist_ok=True)
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("IoT MLP v1 Firmware Export (Experimental)")
print("=" * 80)

# Load model
print("\n[1] Loading model...")
with open(MDIR / "iot_method_b_mlp_pipeline.pkl", 'rb') as f:
    model_obj = pickle.load(f)

scaler = model_obj['scaler']
mlp = model_obj['model']
features = model_obj['features']

print("OK Model loaded")
print("  Features:", features)
print("  MLP: 6 -> 64 -> 32 -> 1")

# ============================================================================
# 1. FEATURE ORDER
# ============================================================================
print("\n[2] Exporting feature order...")
feature_order = {
    "version": "1.0",
    "date": "2026-05-05",
    "status": "experimental_firmware",
    "feature_count": len(features),
    "features": [
        {"index": i, "name": feat, "unit": "V" if "voltage" in feat else "C" if "temperature" in feat else "mA"}
        for i, feat in enumerate(features)
    ],
    "note": "CRITICAL: Features must be in exact order"
}

with open(EXPORT_DIR / "feature_order.json", "w") as f:
    json.dump(feature_order, f, indent=2)
print("OK feature_order.json")

# ============================================================================
# 2. SCALER PARAMS
# ============================================================================
print("\n[3] Exporting scaler parameters...")
scaler_params = {
    "version": "1.0",
    "date": "2026-05-05",
    "type": "MinMaxScaler",
    "data_min": scaler.data_min_.tolist(),
    "data_max": scaler.data_max_.tolist(),
    "scale": scaler.scale_.tolist()
}

with open(EXPORT_DIR / "scaler_params.json", "w") as f:
    json.dump(scaler_params, f, indent=2)
print("OK scaler_params.json")

# ============================================================================
# 3. MLP ARCHITECTURE
# ============================================================================
print("\n[4] Exporting MLP architecture...")
mlp_arch = {
    "version": "1.0",
    "date": "2026-05-05",
    "status": "experimental_firmware",
    "input_size": 6,
    "hidden_layer_sizes": list(mlp.hidden_layer_sizes),
    "output_size": 1,
    "activation": mlp.activation,
    "coef_shapes": [list(c.shape) for c in mlp.coefs_],
    "intercept_shapes": [list(i.shape) for i in mlp.intercepts_]
}

with open(EXPORT_DIR / "mlp_architecture.json", "w") as f:
    json.dump(mlp_arch, f, indent=2)
print("OK mlp_architecture.json")

# ============================================================================
# 4. MLP WEIGHTS (JSON)
# ============================================================================
print("\n[5] Exporting MLP weights (JSON)...")
mlp_weights_json = {
    "version": "1.0",
    "date": "2026-05-05",
    "coefs": [c.tolist() for c in mlp.coefs_],
    "intercepts": [i.tolist() for i in mlp.intercepts_]
}

with open(EXPORT_DIR / "mlp_weights.json", "w") as f:
    json.dump(mlp_weights_json, f, indent=2)
print("OK mlp_weights.json")

# ============================================================================
# 5. MLP WEIGHTS (NPZ)
# ============================================================================
print("\n[6] Exporting MLP weights (NPZ)...")
np.savez(
    EXPORT_DIR / "mlp_weights.npz",
    coef0=mlp.coefs_[0],
    coef1=mlp.coefs_[1],
    coef2=mlp.coefs_[2],
    intercept0=mlp.intercepts_[0],
    intercept1=mlp.intercepts_[1],
    intercept2=mlp.intercepts_[2],
    scaler_min=scaler.data_min_,
    scaler_max=scaler.data_max_,
    scaler_scale=scaler.scale_
)
print("OK mlp_weights.npz")

# ============================================================================
# 6. HEADER PREVIEW
# ============================================================================
print("\n[7] Generating C++ header preview...")
header_content = """// IoT MLP v1 Firmware Weights (Experimental Preview)
// WARNING: Not validated for production
//
// Model: IoT Method B MLP v1 (R²=0.8087)
// Architecture: 6 -> 64 -> 32 -> 1
// Date: 2026-05-05

#ifndef IOT_MLP_WEIGHTS_H
#define IOT_MLP_WEIGHTS_H

#define INPUT_SIZE 6
#define HIDDEN1_SIZE 64
#define HIDDEN2_SIZE 32
#define OUTPUT_SIZE 1

const float SCALER_MIN[6] = {3.87f, 9.41f, 50.1f, -0.06f, -17.7f, -46.3f};
const float SCALER_MAX[6] = {4.21f, 40.19f, 326.3f, 0.02f, 2.18f, 56.8f};
const float SCALER_SCALE[6] = {2.94117647f, 0.032488629f, 0.00362056481f, 12.5f, 0.0503018109f, 0.00969932105f};

// Weights and biases from mlp.coefs_ and mlp.intercepts_
// Full weights data in mlp_weights.npz (binary format)
// Full weights data in mlp_weights.json (text format)

#endif
"""

with open(EXPORT_DIR / "mlp_weights_header_preview.h", "w") as f:
    f.write(header_content)
print("OK mlp_weights_header_preview.h")

# ============================================================================
# 7. VALIDATION SAMPLES
# ============================================================================
print("\n[8] Creating validation samples...")

np.random.seed(42)
synthetic_data = []

for _ in range(20):
    voltage_v = np.random.uniform(3.87, 4.21)
    temperature_c = np.random.uniform(9.41, 40.19)
    current_ma = np.random.uniform(50.1, 326.3)
    delta_voltage = np.random.uniform(-0.06, 0.02)
    delta_temperature = np.random.uniform(-17.7, 2.18)
    delta_current = np.random.uniform(-46.3, 56.8)
    synthetic_data.append([voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current])

validation_samples = pd.DataFrame(synthetic_data, columns=features)
validation_samples.to_csv(SAMPLES_DIR / "export_validation_inputs.csv", index=False)

print("OK validation samples (20 synthetic)")

# ============================================================================
# 8. PREDICT AND VALIDATE
# ============================================================================
print("\n[9] Predicting with original model...")

X_samples = validation_samples[features].values
X_scaled = scaler.transform(X_samples)
y_pred_orig = mlp.predict(X_scaled)
y_pred_orig = np.clip(y_pred_orig, 0, 1)

print("OK predictions shape", y_pred_orig.shape)

# Manual forward pass for validation
def forward_manual(X, coefs, intercepts, scaler_min, scaler_max, scaler_scale):
    X_scaled = (X - scaler_min) * scaler_scale
    # Note: Do NOT clip scaled features; sklearn MLPRegressor allows out-of-range values
    h1 = X_scaled @ coefs[0] + intercepts[0]
    h1 = np.maximum(h1, 0)
    h2 = h1 @ coefs[1] + intercepts[1]
    h2 = np.maximum(h2, 0)
    y = h2 @ coefs[2] + intercepts[2]
    y = np.clip(y, 0, 1)  # Only clip final output to [0, 1]
    return y

y_pred_manual = forward_manual(X_samples, mlp.coefs_, mlp.intercepts_, scaler.data_min_, scaler.data_max_, scaler.scale_)
y_pred_manual = y_pred_manual.flatten()

max_abs_diff = np.max(np.abs(y_pred_orig - y_pred_manual))
mean_abs_diff = np.mean(np.abs(y_pred_orig - y_pred_manual))

print("OK validation comparison")
print("  Max diff: {:.2e}".format(max_abs_diff))
print("  Mean diff: {:.2e}".format(mean_abs_diff))

validation_ok = max_abs_diff < 1e-5

# Save predictions
pred_df = pd.DataFrame(y_pred_orig, columns=['soc_pred_original'])
pred_df['soc_pred_manual'] = y_pred_manual
pred_df['diff'] = np.abs(y_pred_orig - y_pred_manual)
pred_df.to_csv(SAMPLES_DIR / "export_validation_outputs.csv", index=False)

print("OK saved validation outputs")

# ============================================================================
# 9. STATUS CSV
# ============================================================================
print("\n[10] Creating status files...")

status_data = {
    "export_element": [
        "feature_order.json",
        "scaler_params.json",
        "mlp_architecture.json",
        "mlp_weights.json",
        "mlp_weights.npz",
        "mlp_weights_header_preview.h",
        "validation_samples"
    ],
    "status": ["exported"] * 7,
    "date": ["2026-05-05"] * 7
}

status_df = pd.DataFrame(status_data)
status_df.to_csv(ODIR / "iot_mlp_firmware_export_status.csv", index=False)

print("OK iot_mlp_firmware_export_status.csv")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("FIRMWARE EXPORT SUMMARY")
print("=" * 80)
print("\nFeature Order:")
for i, f in enumerate(features):
    print("  {}: {}".format(i, f))

print("\nMLP Architecture:")
print("  Input: 6")
print("  Hidden 1: 64 (ReLU)")
print("  Hidden 2: 32 (ReLU)")
print("  Output: 1 (Linear, clipped to [0,1])")

print("\nScaler (MinMaxScaler):")
print("  Min: {}".format(scaler.data_min_.tolist()[:3]))
print("  Max: {}".format(scaler.data_max_.tolist()[:3]))

print("\nValidation:")
print("  Samples: 20 (synthetic, training range)")
print("  Max diff: {:.2e}".format(max_abs_diff))
print("  Mean diff: {:.2e}".format(mean_abs_diff))
print("  Status: {}".format("PASSED" if validation_ok else "NEEDS_REVIEW"))

print("\nExported Files:")
print("  handoff_esp32_soc_method_b_v1/model/feature_order.json")
print("  handoff_esp32_soc_method_b_v1/model/scaler_params.json")
print("  handoff_esp32_soc_method_b_v1/model/mlp_architecture.json")
print("  handoff_esp32_soc_method_b_v1/model/mlp_weights.json")
print("  handoff_esp32_soc_method_b_v1/model/mlp_weights.npz")
print("  handoff_esp32_soc_method_b_v1/model/mlp_weights_header_preview.h")
print("  handoff_esp32_soc_method_b_v1/samples/export_validation_inputs.csv")
print("  handoff_esp32_soc_method_b_v1/samples/export_validation_outputs.csv")

print("\n[OK] Export complete")
print("=" * 80)
