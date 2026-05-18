from pathlib import Path
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
import joblib
import warnings

warnings.filterwarnings("ignore")

BASE = Path("data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet")
OUT = Path("outputs/external_datasets")
MODELS = Path("models_external")
OUT.mkdir(parents=True, exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "voltage_V",
    "temperature_C",
    "current_abs_A",
    "delta_voltage",
    "delta_temperature",
    "delta_current",
]
TARGET = "soc_target"

MAX_ROWS_PER_CELL = 5000
RANDOM_STATE = 42

print("LG-only Method B balanced cross-cell diagnostic")
print(f"max rows per cell: {MAX_ROWS_PER_CELL}")

files = sorted(BASE.rglob("*.parquet"))
print(f"parts found: {len(files)}")

cols = ["cell_id", "soc_source", TARGET] + FEATURES
buckets = {}

for i, f in enumerate(files, 1):
    try:
        df = pd.read_parquet(f, columns=[c for c in cols if c != "soc_source"])
    except Exception:
        continue

    if "soc_source" in pq.read_schema(f).names:
        df_src = pd.read_parquet(f, columns=["soc_source"])
        df["soc_source"] = df_src["soc_source"].values
        df = df[df["soc_source"].astype(str) == "method_b_lg_recomputed"]

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES + [TARGET, "cell_id"])
    df = df[(df[TARGET] >= 0) & (df[TARGET] <= 1)]

    for cell, g in df.groupby("cell_id"):
        cell = int(cell)
        if cell not in buckets:
            buckets[cell] = []
        current_n = sum(len(x) for x in buckets[cell])
        remaining = MAX_ROWS_PER_CELL - current_n
        if remaining <= 0:
            continue
        if len(g) > remaining:
            g = g.sample(n=remaining, random_state=RANDOM_STATE)
        buckets[cell].append(g[["cell_id"] + FEATURES + [TARGET]])

    if i % 20 == 0:
        loaded = sum(sum(len(x) for x in v) for v in buckets.values())
        print(f"processed parts: {i}/{len(files)} | sampled rows: {loaded}")

sample_parts = []
for cell, parts in buckets.items():
    if parts:
        sample_parts.append(pd.concat(parts, ignore_index=True))

data = pd.concat(sample_parts, ignore_index=True)
data = data.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)

cells = sorted(data["cell_id"].unique())
print(f"sample rows: {len(data)}")
print(f"cells: {cells}")

metrics = []

for idx, test_cell in enumerate(cells, 1):
    train = data[data["cell_id"] != test_cell]
    test = data[data["cell_id"] == test_cell]

    X_train = train[FEATURES].values
    y_train = train[TARGET].values
    X_test = test[FEATURES].values
    y_test = test[TARGET].values

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("mlp", MLPRegressor(
            hidden_layer_sizes=(32, 16),
            activation="relu",
            solver="adam",
            max_iter=80,
            early_stopping=True,
            random_state=RANDOM_STATE,
            verbose=False
        ))
    ])

    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    pred_clip = np.clip(pred, 0, 1)

    r2 = r2_score(y_test, pred_clip)
    mae = mean_absolute_error(y_test, pred_clip)
    rmse = mean_squared_error(y_test, pred_clip) ** 0.5
    bias = float(np.mean(pred_clip - y_test))

    metrics.append({
        "test_cell": int(test_cell),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "R2": float(r2),
        "MAE": float(mae),
        "RMSE": float(rmse),
        "bias": bias,
        "pred_min": float(pred.min()),
        "pred_max": float(pred.max()),
        "pred_clip_min": float(pred_clip.min()),
        "pred_clip_max": float(pred_clip.max()),
        "target_min": float(y_test.min()),
        "target_max": float(y_test.max()),
    })

    print(f"{idx}/{len(cells)} cell={test_cell} R2={r2:.4f} MAE={mae:.4f} RMSE={rmse:.4f}")

metrics_df = pd.DataFrame(metrics)
metrics_path = OUT / "lg_only_method_b_balanced_cross_cell_metrics.csv"
summary_path = OUT / "lg_only_method_b_balanced_cross_cell_summary.md"

metrics_df.to_csv(metrics_path, index=False)

mean_r2 = metrics_df["R2"].mean()
std_r2 = metrics_df["R2"].std()
mean_mae = metrics_df["MAE"].mean()
std_mae = metrics_df["MAE"].std()
mean_rmse = metrics_df["RMSE"].mean()
std_rmse = metrics_df["RMSE"].std()

best = metrics_df.loc[metrics_df["R2"].idxmax()]
worst = metrics_df.loc[metrics_df["R2"].idxmin()]

decision = "LG_ONLY_METHOD_B_BALANCED_READY"
if mean_r2 < 0.5:
    decision = "LG_ONLY_METHOD_B_BALANCED_WEAK"

summary = f"""# LG-only Method B Balanced Cross-cell

## Status
{decision}

## Dataset
- Subset: clean_all_valid Method B
- Sample rows: {len(data)}
- Cells: {len(cells)}
- Max rows per cell: {MAX_ROWS_PER_CELL}
- Features: {", ".join(FEATURES)}
- Target: soc_target = method_b_lg_recomputed

## Metrics
- R2 mean/std: {mean_r2:.4f} / {std_r2:.4f}
- MAE mean/std: {mean_mae:.4f} / {std_mae:.4f}
- RMSE mean/std: {mean_rmse:.4f} / {std_rmse:.4f}
- Best cell: {int(best["test_cell"])} | R2={best["R2"]:.4f}
- Worst cell: {int(worst["test_cell"])} | R2={worst["R2"]:.4f}

## Interpretation
- This is a balanced diagnostic, not the full 4.8M-row final training.
- It tests whether Method B LG can learn cross-cell under bounded compute.
- Use full training later only if needed.
"""

summary_path.write_text(summary, encoding="utf-8")

# train one deployable diagnostic model on the balanced sample
final_model = Pipeline([
    ("scaler", StandardScaler()),
    ("mlp", MLPRegressor(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="adam",
        max_iter=120,
        early_stopping=True,
        random_state=RANDOM_STATE,
        verbose=False
    ))
])
final_model.fit(data[FEATURES].values, data[TARGET].values)
joblib.dump(final_model, MODELS / "lg18650_method_b_balanced_mlp_pipeline.pkl")

print("saved:", metrics_path)
print("saved:", summary_path)
print("saved:", MODELS / "lg18650_method_b_balanced_mlp_pipeline.pkl")
print("decision:", decision)
