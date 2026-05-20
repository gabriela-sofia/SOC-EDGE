from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    from analyze_v8b2_model_footprint import DEFAULT_HEADER, load_header, parse_float_arrays
    from v8c_python_float_vs_candidate_benchmark import (
        CONSERVATIVE_MAX_ABS_DIFF_LIMIT,
        DEFAULT_REPLAY_CSVS,
        clip_soc,
        load_rows,
    )
except ModuleNotFoundError:
    from scripts.analyze_v8b2_model_footprint import DEFAULT_HEADER, load_header, parse_float_arrays
    from scripts.v8c_python_float_vs_candidate_benchmark import (
        CONSERVATIVE_MAX_ABS_DIFF_LIMIT,
        DEFAULT_REPLAY_CSVS,
        clip_soc,
        load_rows,
    )


DEFAULT_OUTPUT_DIR = Path("reports/v8c_quant_benchmark")
DEFAULT_OPTIMIZED_HEADER = Path("embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model_optimized.h")
FEATURE_ORDER = [
    "voltage_v",
    "temperature_c",
    "current_ma",
    "delta_voltage",
    "delta_temperature",
    "delta_current",
]


@dataclass(frozen=True)
class QuantizedMatrix:
    values: list[list[int]]
    scales: list[float]
    bit_width: int


@dataclass(frozen=True)
class VariantSpec:
    variant_id: str
    strategy: str
    weight_mode: str
    bias_mode: str
    notes: str


VARIANTS = [
    VariantSpec(
        variant_id="v8c_int8_per_array_candidate",
        strategy="INT8 symmetric per-array for weights and biases",
        weight_mode="int8_per_array",
        bias_mode="int8_per_array",
        notes="Current tracked candidate; preserved for traceability.",
    ),
    VariantSpec(
        variant_id="v8c_int8_per_output_bias_float",
        strategy="INT8 symmetric per-output-channel weights with float biases",
        weight_mode="int8_per_output",
        bias_mode="float",
        notes="Compact weights while preserving bias precision.",
    ),
    VariantSpec(
        variant_id="v8c_int8_per_output_bias_int8",
        strategy="INT8 symmetric per-output-channel weights with INT8 per-array biases",
        weight_mode="int8_per_output",
        bias_mode="int8_per_array",
        notes="Fully INT8 weights and biases with per-output weight scales.",
    ),
    VariantSpec(
        variant_id="v8c_mixed_w0_w1_int8_w2_bias_float",
        strategy="Mixed precision: W0/W1 INT8 per-output, W2 and biases float",
        weight_mode="mixed_w0_w1_int8_w2_float",
        bias_mode="float",
        notes="Conservative trade-off: compact hidden layers and preserve output layer precision.",
    ),
    VariantSpec(
        variant_id="v8c_int16_per_output_bias_float",
        strategy="INT16 symmetric per-output-channel weights with float biases",
        weight_mode="int16_per_output",
        bias_mode="float",
        notes="Alternative fixed-point candidate if INT8 does not meet the conservative parity limit.",
    ),
]


def c_float(value: float) -> str:
    text = f"{value:.10g}"
    if "e" not in text.lower() and "." not in text:
        text += ".0"
    return text + "f"


def scale_for_values(values: list[float], max_q: int) -> float:
    max_abs = max(abs(value) for value in values) if values else 0.0
    return max_abs / max_q if max_abs else 1.0


def quantize_value(value: float, scale: float, max_q: int) -> int:
    return max(-max_q, min(max_q, round(value / scale)))


def quantize_matrix_per_array(matrix: list[list[float]], bit_width: int) -> QuantizedMatrix:
    max_q = (2 ** (bit_width - 1)) - 1
    flat = [value for row in matrix for value in row]
    scale = scale_for_values(flat, max_q)
    return QuantizedMatrix(
        values=[[quantize_value(value, scale, max_q) for value in row] for row in matrix],
        scales=[scale],
        bit_width=bit_width,
    )


def quantize_matrix_per_output(matrix: list[list[float]], bit_width: int) -> QuantizedMatrix:
    max_q = (2 ** (bit_width - 1)) - 1
    n_outputs = len(matrix[0]) if matrix else 0
    scales = []
    for output_index in range(n_outputs):
        column = [row[output_index] for row in matrix]
        scales.append(scale_for_values(column, max_q))
    quantized = []
    for row in matrix:
        quantized.append(
            [quantize_value(value, scales[index], max_q) for index, value in enumerate(row)]
        )
    return QuantizedMatrix(values=quantized, scales=scales, bit_width=bit_width)


def quantize_vector_per_array(values: list[float], bit_width: int) -> tuple[list[int], float]:
    max_q = (2 ** (bit_width - 1)) - 1
    scale = scale_for_values(values, max_q)
    return [quantize_value(value, scale, max_q) for value in values], scale


def dequant_matrix(quantized: QuantizedMatrix) -> list[list[float]]:
    output = []
    per_output = len(quantized.scales) > 1
    for row in quantized.values:
        output.append(
            [
                value * (quantized.scales[index] if per_output else quantized.scales[0])
                for index, value in enumerate(row)
            ]
        )
    return output


def relu(value: float) -> float:
    return value if value > 0.0 else 0.0


def reshape(values: list[float], dimensions: list[int]) -> list:
    if len(dimensions) == 1:
        return list(values)
    if len(dimensions) == 2:
        rows, cols = dimensions
        return [values[index * cols : (index + 1) * cols] for index in range(rows)]
    raise ValueError(f"Unsupported dimensions: {dimensions}")


def load_baseline_arrays(header: Path) -> dict[str, list]:
    arrays = {}
    for array in parse_float_arrays(load_header(header)):
        arrays[array.name] = reshape(array.values, array.dimensions)
    required = ["SCALER_MIN", "SCALER_SCALE", "W0", "B0", "W1", "B1", "W2", "B2"]
    missing = [name for name in required if name not in arrays]
    if missing:
        raise ValueError("Missing arrays: " + ", ".join(missing))
    return arrays


def build_variant_arrays(base: dict[str, list], spec: VariantSpec) -> dict[str, object]:
    if spec.weight_mode == "int8_per_array":
        w0_q = quantize_matrix_per_array(base["W0"], 8)
        w1_q = quantize_matrix_per_array(base["W1"], 8)
        w2_q = quantize_matrix_per_array(base["W2"], 8)
    elif spec.weight_mode == "int8_per_output":
        w0_q = quantize_matrix_per_output(base["W0"], 8)
        w1_q = quantize_matrix_per_output(base["W1"], 8)
        w2_q = quantize_matrix_per_output(base["W2"], 8)
    elif spec.weight_mode == "mixed_w0_w1_int8_w2_float":
        w0_q = quantize_matrix_per_output(base["W0"], 8)
        w1_q = quantize_matrix_per_output(base["W1"], 8)
        w2_q = None
    elif spec.weight_mode == "int16_per_output":
        w0_q = quantize_matrix_per_output(base["W0"], 16)
        w1_q = quantize_matrix_per_output(base["W1"], 16)
        w2_q = quantize_matrix_per_output(base["W2"], 16)
    else:
        raise ValueError(f"Unsupported weight mode: {spec.weight_mode}")

    if spec.bias_mode == "float":
        b0 = base["B0"]
        b1 = base["B1"]
        b2 = base["B2"]
        b0_q = b1_q = b2_q = None
    elif spec.bias_mode == "int8_per_array":
        b0_q = quantize_vector_per_array(base["B0"], 8)
        b1_q = quantize_vector_per_array(base["B1"], 8)
        b2_q = quantize_vector_per_array(base["B2"], 8)
        b0 = [value * b0_q[1] for value in b0_q[0]]
        b1 = [value * b1_q[1] for value in b1_q[0]]
        b2 = [value * b2_q[1] for value in b2_q[0]]
    else:
        raise ValueError(f"Unsupported bias mode: {spec.bias_mode}")

    return {
        "W0": dequant_matrix(w0_q),
        "B0": b0,
        "W1": dequant_matrix(w1_q),
        "B1": b1,
        "W2": base["W2"] if w2_q is None else dequant_matrix(w2_q),
        "B2": b2,
        "W0_Q": w0_q,
        "W1_Q": w1_q,
        "W2_Q": w2_q,
        "B0_Q": b0_q,
        "B1_Q": b1_q,
        "B2_Q": b2_q,
    }


def predict_arrays(arrays: dict[str, list], features: list[float]) -> float:
    scaled = [
        (features[index] - arrays["SCALER_MIN"][index]) * arrays["SCALER_SCALE"][index]
        for index in range(len(features))
    ]
    h0 = []
    for j in range(len(arrays["B0"])):
        acc = arrays["B0"][j]
        for i in range(len(scaled)):
            acc += scaled[i] * arrays["W0"][i][j]
        h0.append(relu(acc))
    h1 = []
    for j in range(len(arrays["B1"])):
        acc = arrays["B1"][j]
        for i in range(len(h0)):
            acc += h0[i] * arrays["W1"][i][j]
        h1.append(relu(acc))
    out = arrays["B2"][0]
    for i in range(len(h1)):
        out += h1[i] * arrays["W2"][i][0]
    return clip_soc(out)


def metric_summary(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "mae": statistics.fmean(abs(value) for value in values),
        "rmse": math.sqrt(statistics.fmean(value * value for value in values)),
        "max_abs_diff": max(abs(value) for value in values),
    }


def evaluate_variant(base: dict[str, list], rows: list[dict[str, object]], spec: VariantSpec) -> tuple[dict[str, object], dict[str, object]]:
    variant_arrays = build_variant_arrays(base, spec)
    model_arrays = {
        "SCALER_MIN": base["SCALER_MIN"],
        "SCALER_SCALE": base["SCALER_SCALE"],
        "W0": variant_arrays["W0"],
        "B0": variant_arrays["B0"],
        "W1": variant_arrays["W1"],
        "B1": variant_arrays["B1"],
        "W2": variant_arrays["W2"],
        "B2": variant_arrays["B2"],
    }
    diffs = []
    candidate_socs = []
    for row in rows:
        baseline_soc = predict_arrays(base, row["features"])
        candidate_soc = predict_arrays(model_arrays, row["features"])
        candidate_socs.append(candidate_soc)
        diffs.append(candidate_soc - baseline_soc)
    metrics = metric_summary(diffs)
    nonfinite = sum(1 for value in candidate_socs + diffs if not math.isfinite(value))
    row = {
        "variant_id": spec.variant_id,
        "quantization_strategy": spec.strategy,
        "n_samples": metrics["n"],
        "mae_vs_float": metrics["mae"],
        "rmse_vs_float": metrics["rmse"],
        "max_abs_diff_vs_float": metrics["max_abs_diff"],
        "nan_inf_count": nonfinite,
        "candidate_soc_min": min(candidate_socs),
        "candidate_soc_max": max(candidate_socs),
        "within_conservative_limit": metrics["max_abs_diff"] <= CONSERVATIVE_MAX_ABS_DIFF_LIMIT,
        "approx_weight_bytes": approximate_weight_bytes(spec),
        "notes": spec.notes,
    }
    return row, variant_arrays


def approximate_weight_bytes(spec: VariantSpec) -> int:
    if spec.weight_mode == "int16_per_output":
        weight_bytes = (6 * 64 + 64 * 32 + 32 * 1) * 2
    elif spec.weight_mode == "mixed_w0_w1_int8_w2_float":
        weight_bytes = (6 * 64 + 64 * 32) + (32 * 1 * 4)
    else:
        weight_bytes = 6 * 64 + 64 * 32 + 32 * 1
    bias_bytes = (64 + 32 + 1) * (4 if spec.bias_mode == "float" else 1)
    return weight_bytes + bias_bytes


def rank_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            float(row["max_abs_diff_vs_float"]),
            float(row["mae_vs_float"]),
            float(row["rmse_vs_float"]),
            int(row["approx_weight_bytes"]),
        ),
    )


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "variant_id",
        "quantization_strategy",
        "n_samples",
        "mae_vs_float",
        "rmse_vs_float",
        "max_abs_diff_vs_float",
        "nan_inf_count",
        "candidate_soc_min",
        "candidate_soc_max",
        "within_conservative_limit",
        "approx_weight_bytes",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def c_float(value: float) -> str:
    text = f"{value:.10g}"
    if "e" not in text.lower() and "." not in text:
        text += ".0"
    return text + "f"


def c_float_array(name: str, values: list[float]) -> str:
    return f"static const float {name}[{len(values)}] = {{ " + ", ".join(c_float(value) for value in values) + " };"


def c_matrix_int(name: str, quantized: QuantizedMatrix, c_type: str) -> str:
    rows = len(quantized.values)
    cols = len(quantized.values[0])
    lines = [f"static const {c_type} {name}[{rows}][{cols}] = {{"]
    for row_index, row in enumerate(quantized.values):
        suffix = "," if row_index < rows - 1 else ""
        lines.append("  { " + ", ".join(str(value) for value in row) + " }" + suffix)
    lines.append("};")
    return "\n".join(lines)


def render_optimized_header(base: dict[str, list], variant_arrays: dict[str, object], best: dict[str, object]) -> str:
    w0_q: QuantizedMatrix = variant_arrays["W0_Q"]
    w1_q: QuantizedMatrix = variant_arrays["W1_Q"]
    w2_q = variant_arrays["W2_Q"]
    int_type = "int16_t" if w0_q.bit_width == 16 else "int8_t"
    lines = [
        "/*",
        " * SOC-EDGE V8C optimized experimental quantized candidate.",
        " * Baseline remains MLP V7C/V8B2 float; this header does not replace it.",
        f" * Variant: {best['variant_id']}",
        f" * Strategy: {best['quantization_strategy']}",
        f" * Offline max_abs_diff_vs_float: {best['max_abs_diff_vs_float']}",
        f" * Conservative max_abs_diff limit: {CONSERVATIVE_MAX_ABS_DIFF_LIMIT}",
        f" * Within conservative limit: {str(best['within_conservative_limit']).lower()}",
        " * ESP32 execution is still required for latency, heap, and parity logs.",
        " */",
        "#ifndef SOC_EDGE_V8C_CANDIDATE_QUANTIZED_MODEL_OPTIMIZED_H",
        "#define SOC_EDGE_V8C_CANDIDATE_QUANTIZED_MODEL_OPTIMIZED_H",
        "",
        "#include <math.h>",
        "#include <stdint.h>",
        "",
        "#define V8C_OPTIMIZED_CANDIDATE_EXPERIMENTAL 1",
        "#define MLP_INPUT_SIZE 6",
        "#define MLP_L0_SIZE 64",
        "#define MLP_L1_SIZE 32",
        "#define MLP_OUTPUT_SIZE 1",
        "#define V8C_OPTIMIZED_PARAMETER_COUNT 2561",
        "",
        "/* Feature order: voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current */",
        "/* Units: voltage_v V, temperature_c C, current_ma mA, delta_voltage V, delta_temperature C, delta_current mA */",
        "/* Scaler: x_scaled[i] = (x[i] - SCALER_MIN[i]) * SCALER_SCALE[i]; do not clip scaled features. */",
        "/* Output: clip only final SOC to [0, 1]. */",
        "",
        c_float_array("SCALER_MIN", base["SCALER_MIN"]),
        c_float_array("SCALER_SCALE", base["SCALER_SCALE"]),
        c_float_array("W0_SCALES", w0_q.scales),
        c_float_array("W1_SCALES", w1_q.scales),
    ]
    if w2_q is not None:
        lines.append(c_float_array("W2_SCALES", w2_q.scales))
    lines.extend(
        [
            c_matrix_int("W0_Q", w0_q, int_type),
            c_matrix_int("W1_Q", w1_q, int_type),
        ]
    )
    if w2_q is None:
        lines.append("static const float W2_FLOAT[32][1] = {")
        for row_index, row in enumerate(base["W2"]):
            suffix = "," if row_index < len(base["W2"]) - 1 else ""
            lines.append("  { " + c_float(row[0]) + " }" + suffix)
        lines.append("};")
    else:
        lines.append(c_matrix_int("W2_Q", w2_q, int_type))
    lines.extend(
        [
            c_float_array("B0_FLOAT", base["B0"]),
            c_float_array("B1_FLOAT", base["B1"]),
            c_float_array("B2_FLOAT", base["B2"]),
            "",
            "static inline float v8c_optimized_dequant_weight(int value, float scale) {",
            "  return ((float)value) * scale;",
            "}",
            "",
            "static inline float candidate_optimized_mlp_predict(const float x_raw[6]) {",
            "  float x[MLP_INPUT_SIZE];",
            "  for (int i = 0; i < MLP_INPUT_SIZE; ++i) {",
            "    x[i] = (x_raw[i] - SCALER_MIN[i]) * SCALER_SCALE[i];",
            "  }",
            "",
            "  float h0[MLP_L0_SIZE];",
            "  for (int j = 0; j < MLP_L0_SIZE; ++j) {",
            "    float acc = B0_FLOAT[j];",
            "    for (int i = 0; i < MLP_INPUT_SIZE; ++i) {",
            "      acc += v8c_optimized_dequant_weight(W0_Q[i][j], W0_SCALES[j]) * x[i];",
            "    }",
            "    h0[j] = fmaxf(0.0f, acc);",
            "  }",
            "",
            "  float h1[MLP_L1_SIZE];",
            "  for (int j = 0; j < MLP_L1_SIZE; ++j) {",
            "    float acc = B1_FLOAT[j];",
            "    for (int i = 0; i < MLP_L0_SIZE; ++i) {",
            "      acc += v8c_optimized_dequant_weight(W1_Q[i][j], W1_SCALES[j]) * h0[i];",
            "    }",
            "    h1[j] = fmaxf(0.0f, acc);",
            "  }",
            "",
            "  float out = B2_FLOAT[0];",
            "  for (int i = 0; i < MLP_L1_SIZE; ++i) {",
        ]
    )
    if w2_q is None:
        lines.append("    out += W2_FLOAT[i][0] * h1[i];")
    else:
        lines.append("    out += v8c_optimized_dequant_weight(W2_Q[i][0], W2_SCALES[0]) * h1[i];")
    lines.extend(
        [
            "  }",
            "  return fmaxf(0.0f, fminf(1.0f, out));",
            "}",
            "",
            "#endif",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Optimize V8C quantized candidates without retraining.")
    parser.add_argument("--baseline-header", type=Path, default=DEFAULT_HEADER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ranking-csv", type=Path)
    parser.add_argument("--ranking-json", type=Path)
    parser.add_argument("--optimized-header", type=Path, default=DEFAULT_OPTIMIZED_HEADER)
    parser.add_argument("--replay-csv", type=Path, action="append")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = load_baseline_arrays(args.baseline_header)
    replay_paths = args.replay_csv or DEFAULT_REPLAY_CSVS
    rows = load_rows(replay_paths)
    metrics_rows = []
    variant_payloads = {}
    for spec in VARIANTS:
        row, payload = evaluate_variant(base, rows, spec)
        metrics_rows.append(row)
        variant_payloads[spec.variant_id] = payload
    ranked = rank_rows(metrics_rows)
    best = ranked[0]
    csv_path = args.ranking_csv or args.output_dir / "v8c_quantized_variant_ranking.csv"
    json_path = args.ranking_json or args.output_dir / "v8c_quantized_variant_ranking_summary.json"
    write_csv(csv_path, ranked)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_header": args.baseline_header.as_posix(),
        "replay_files": [path.as_posix() for path in replay_paths],
        "conservative_max_abs_diff_limit": CONSERVATIVE_MAX_ABS_DIFF_LIMIT,
        "best_variant_id": best["variant_id"],
        "best_variant_within_conservative_limit": best["within_conservative_limit"],
        "variants_ranked": ranked,
        "optimized_header": None,
        "notes": "All variants are experimental and do not replace the V8B2 float baseline.",
    }
    current = next(row for row in ranked if row["variant_id"] == "v8c_int8_per_array_candidate")
    if float(best["max_abs_diff_vs_float"]) < float(current["max_abs_diff_vs_float"]):
        args.optimized_header.parent.mkdir(parents=True, exist_ok=True)
        args.optimized_header.write_text(
            render_optimized_header(base, variant_payloads[best["variant_id"]], best),
            encoding="utf-8",
        )
        summary["optimized_header"] = args.optimized_header.as_posix()
    write_json(json_path, summary)
    print(f"ranking_csv: {csv_path}")
    print(f"ranking_json: {json_path}")
    print(f"best_variant_id: {best['variant_id']}")
    print(f"best_max_abs_diff_vs_float: {best['max_abs_diff_vs_float']}")
    print(f"within_conservative_limit: {best['within_conservative_limit']}")
    if summary["optimized_header"]:
        print(f"optimized_header: {summary['optimized_header']}")
    else:
        print("optimized_header: NOT_EXPORTED_NO_IMPROVEMENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
