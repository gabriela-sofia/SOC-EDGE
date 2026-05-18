from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import warnings

warnings.filterwarnings("ignore")

ROOT = Path(".")
OUT = ROOT / "outputs" / "external_datasets"
REPORTS = ROOT / "REPORTS"
OUT.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

OX_MODEL = ROOT / "CORE" / "stage4c_final_results" / "models" / "best_mlp_exp_A_split1.pkl"
OX_SCALER = ROOT / "CORE" / "stage4c_final_results" / "models" / "scaler_exp_A_split1.pkl"
IOT = OUT / "iot_method_b_extracted.parquet"
IOT_METRICS = OUT / "iot_method_b_diagnostic_metrics.csv"

FEATURES = [
    "voltage_V",
    "temperature_C",
    "current_abs_A",
    "delta_voltage",
    "delta_temperature",
    "delta_current",
]

print("Loading Oxford model/scaler...")
model = joblib.load(OX_MODEL)
scaler = joblib.load(OX_SCALER)

print("Loading IoT Method B dataset...")
df = pd.read_parquet(IOT)
print("Columns:", list(df.columns))

# -------------------------
# Column mapping
# -------------------------
rename = {}

if "voltage_v" in df.columns:
    rename["voltage_v"] = "voltage_V"
elif "Battery Voltage" in df.columns:
    rename["Battery Voltage"] = "voltage_V"

if "temperature_c" in df.columns:
    rename["temperature_c"] = "temperature_C"
elif "Temperature" in df.columns:
    rename["Temperature"] = "temperature_C"

df = df.rename(columns=rename)

# Current in A
if "current_abs_A" not in df.columns:
    if "current_abs_a" in df.columns:
        df["current_abs_A"] = df["current_abs_a"].abs()
    elif "current_a" in df.columns:
        df["current_abs_A"] = df["current_a"].abs()
    elif "current_A" in df.columns:
        df["current_abs_A"] = df["current_A"].abs()
    elif "current_ma" in df.columns:
        df["current_abs_A"] = df["current_ma"].abs() / 1000.0
    elif "Battery Current" in df.columns:
        # assume mA if magnitude suggests mA
        cur = pd.to_numeric(df["Battery Current"], errors="coerce")
        df["current_abs_A"] = cur.abs() / 1000.0 if cur.abs().quantile(0.99) > 20 else cur.abs()
    else:
        raise KeyError("No current column found for current_abs_A")

# Target
if "soc_method_b" in df.columns:
    target_col = "soc_method_b"
elif "soc_target" in df.columns:
    target_col = "soc_target"
else:
    raise KeyError("No Method B SOC target found: expected soc_method_b or soc_target")

# -------------------------
# Sorting/grouping for deltas
# -------------------------
group_cols = []
for c in ["node_id", "node", "device_id", "sensor_id"]:
    if c in df.columns:
        group_cols = [c]
        break

time_col = None
for c in ["timestamp", "datetime", "date_time", "time", "Time", "DateTime"]:
    if c in df.columns:
        time_col = c
        break

if time_col is not None:
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    sort_cols = group_cols + [time_col] if group_cols else [time_col]
    df = df.sort_values(sort_cols).reset_index(drop=True)
else:
    df = df.reset_index(drop=True)

# -------------------------
# Delta creation if missing
# -------------------------
def grouped_diff(col):
    if group_cols:
        return df.groupby(group_cols, sort=False)[col].diff().fillna(0)
    return df[col].diff().fillna(0)

if "delta_voltage" not in df.columns:
    df["delta_voltage"] = grouped_diff("voltage_V")

if "delta_temperature" not in df.columns:
    df["delta_temperature"] = grouped_diff("temperature_C")

if "delta_current" not in df.columns:
    df["delta_current"] = grouped_diff("current_abs_A")

# Unit fix: if delta_current is clearly mA scale, convert to A
if df["delta_current"].abs().quantile(0.99) > 20:
    df["delta_current"] = df["delta_current"] / 1000.0

# -------------------------
# Cleaning
# -------------------------
df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna(subset=FEATURES + [target_col])
df = df[(df[target_col] >= 0) & (df[target_col] <= 1)]

X = df[FEATURES].astype(float).values
y = df[target_col].astype(float).values

print(f"Rows valid: {len(df)}")
print("Features:", FEATURES)
print("Target:", target_col)

# -------------------------
# Oxford frozen model eval
# -------------------------
print("Evaluating Oxford frozen model on IoT...")
X_scaled = scaler.transform(X)
pred_raw = model.predict(X_scaled)
pred_clip = np.clip(pred_raw, 0, 1)

def make_metrics(name, pred, pred_for_oob=None):
    if pred_for_oob is None:
        pred_for_oob = pred
    return {
        "model": name,
        "rows": len(y),
        "R2": r2_score(y, pred),
        "MAE": mean_absolute_error(y, pred),
        "RMSE": mean_squared_error(y, pred) ** 0.5,
        "bias": float(np.mean(pred - y)),
        "pred_min": float(np.min(pred)),
        "pred_max": float(np.max(pred)),
        "pred_oob_rate": float(np.mean((pred_for_oob < 0) | (pred_for_oob > 1))),
        "target_min": float(np.min(y)),
        "target_max": float(np.max(y)),
    }

rows = [
    make_metrics("oxford_frozen_raw", pred_raw, pred_raw),
    make_metrics("oxford_frozen_clipped", pred_clip, pred_raw),
]

# Add IoT-only reference from previous metrics if available
if IOT_METRICS.exists():
    m = pd.read_csv(IOT_METRICS)
    if "model" in m.columns:
        mlp = m[m["model"].astype(str).str.contains("MLP", case=False, na=False)]
    else:
        mlp = m[m.astype(str).apply(lambda r: r.str.contains("MLP", case=False, na=False).any(), axis=1)]

    if not mlp.empty:
        ref = {"model": "iot_only_mlp_reference", "rows": len(y)}
        for c in ["R2", "MAE", "RMSE", "bias"]:
            if c in mlp.columns:
                ref[c] = float(pd.to_numeric(mlp[c], errors="coerce").mean())
        rows.append(ref)

metrics_df = pd.DataFrame(rows)
metrics_path = OUT / "oxford_vs_iot_method_b_metrics.csv"
metrics_df.to_csv(metrics_path, index=False)

# -------------------------
# Scaler/OOD diagnostic
# -------------------------
scaled = scaler.transform(X)
ood_rows = []
for i, feat in enumerate(FEATURES):
    raw_vals = X[:, i]
    scaled_vals = scaled[:, i]
    ood_rows.append({
        "feature": feat,
        "raw_min": float(np.min(raw_vals)),
        "raw_max": float(np.max(raw_vals)),
        "raw_mean": float(np.mean(raw_vals)),
        "scaled_min": float(np.min(scaled_vals)),
        "scaled_max": float(np.max(scaled_vals)),
        "scaled_abs_gt_3_rate": float(np.mean(np.abs(scaled_vals) > 3)),
        "scaled_abs_gt_5_rate": float(np.mean(np.abs(scaled_vals) > 5)),
        "scaled_abs_gt_10_rate": float(np.mean(np.abs(scaled_vals) > 10)),
    })

ood_df = pd.DataFrame(ood_rows)
ood_path = OUT / "oxford_vs_iot_method_b_ood_diagnostic.csv"
ood_df.to_csv(ood_path, index=False)

raw = metrics_df[metrics_df["model"] == "oxford_frozen_raw"].iloc[0]
clip = metrics_df[metrics_df["model"] == "oxford_frozen_clipped"].iloc[0]

decision = "OXFORD_FAILS_IOT_DOMAIN_SHIFT"
if clip["R2"] > 0.5 and clip["MAE"] < 0.15:
    decision = "OXFORD_PARTIALLY_GENERALIZES_TO_IOT"

if ood_df["scaled_abs_gt_10_rate"].max() > 0.1:
    decision = "FEATURE_UNIT_FIX_NEEDED_OR_OXFORD_FAILS_IOT_DOMAIN_SHIFT"

iot_ref = ""
if "iot_only_mlp_reference" in set(metrics_df["model"]):
    ref = metrics_df[metrics_df["model"] == "iot_only_mlp_reference"].iloc[0]
    iot_ref = f"""
## IoT-only reference
- R2 medio: {ref.get('R2', np.nan):.4f}
- MAE medio: {ref.get('MAE', np.nan):.4f}
- RMSE medio: {ref.get('RMSE', np.nan):.4f}
"""

report = f"""# Cross-domain Validation - Oxford vs IoT Method B

## Objetivo
Avaliar se o modelo Oxford Stage4C congelado generaliza para o dataset IoT Energy Harvesting com Method B parcial/windowed.

## Target
- IoT target: {target_col}
- Linhas validas: {len(df)}
- Features: {", ".join(FEATURES)}

## Oxford frozen on IoT
- R2 raw: {raw['R2']:.4f}
- MAE raw: {raw['MAE']:.4f}
- RMSE raw: {raw['RMSE']:.4f}
- Bias raw: {raw['bias']:.4f}
- Pred raw range: [{raw['pred_min']:.4f}, {raw['pred_max']:.4f}]
- OOB raw rate: {raw['pred_oob_rate']:.4f}

## Oxford clipped on IoT
- R2 clipped: {clip['R2']:.4f}
- MAE clipped: {clip['MAE']:.4f}
- RMSE clipped: {clip['RMSE']:.4f}
- Bias clipped: {clip['bias']:.4f}
{iot_ref}
## OOD diagnostic
- Maior taxa scaled_abs>3: {ood_df['scaled_abs_gt_3_rate'].max():.4f}
- Maior taxa scaled_abs>5: {ood_df['scaled_abs_gt_5_rate'].max():.4f}
- Maior taxa scaled_abs>10: {ood_df['scaled_abs_gt_10_rate'].max():.4f}
- Feature mais OOD: {ood_df.loc[ood_df['scaled_abs_gt_10_rate'].idxmax(), 'feature']}

## Interpretacao
O IoT opera em regime partial-cycle/low-current/field-like. A comparacao testa portabilidade do modelo Oxford, nao validade do target Method B.

## Decisao
{decision}
"""

report_path = REPORTS / "10_CROSS_DOMAIN_VALIDATION_OXFORD_VS_IOT.md"
report_path.write_text(report, encoding="utf-8")

print("saved:", metrics_path)
print("saved:", ood_path)
print("saved:", report_path)
print("decision:", decision)
print(metrics_df)
