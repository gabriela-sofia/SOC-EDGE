from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    from analyze_v8b2_model_footprint import DEFAULT_HEADER, is_model_parameter_array, load_header, parse_defines, parse_float_arrays
    from compare_v8b2_float_vs_dequantized import (
        DEFAULT_OUTPUT_DIR,
        DEFAULT_REPLAY_CSVS,
        compute_metrics,
        predict,
        read_replay_csv,
        reshape,
    )
except ModuleNotFoundError:
    from scripts.analyze_v8b2_model_footprint import DEFAULT_HEADER, is_model_parameter_array, load_header, parse_defines, parse_float_arrays
    from scripts.compare_v8b2_float_vs_dequantized import (
        DEFAULT_OUTPUT_DIR,
        DEFAULT_REPLAY_CSVS,
        compute_metrics,
        predict,
        read_replay_csv,
        reshape,
    )


SCHEMES = [
    "global_symmetric_int8",
    "per_array_symmetric_int8",
    "per_layer_group_symmetric_int8",
]
MODEL_ARRAYS = {"W0", "B0", "W1", "B1", "W2", "B2"}
LAYER_GROUPS = {
    "L0": {"W0", "B0"},
    "L1": {"W1", "B1"},
    "L2": {"W2", "B2"},
}


def quantize_with_scale(values: list[float], scale: float) -> list[float]:
    output: list[float] = []
    for value in values:
        quantized = round(value / scale)
        quantized = max(-127, min(127, quantized))
        output.append(quantized * scale)
    return output


def scale_for_values(values: list[float]) -> float:
    max_abs = max((abs(value) for value in values), default=0.0)
    return max_abs / 127.0 if max_abs != 0.0 else 1.0


def model_arrays(text: str):
    return [array for array in parse_float_arrays(text) if is_model_parameter_array(array.name)]


def make_dequantized_arrays(text: str, scheme: str) -> tuple[dict[str, list], dict[str, float], list[str]]:
    arrays = parse_float_arrays(text)
    warnings: list[str] = []
    scales: dict[str, float] = {}
    dequantized_values: dict[str, list[float]] = {}

    if scheme == "global_symmetric_int8":
        values = [value for array in arrays if is_model_parameter_array(array.name) for value in array.values]
        scale = scale_for_values(values)
        scales["GLOBAL"] = scale
        for array in arrays:
            dequantized_values[array.name] = (
                quantize_with_scale(array.values, scale) if is_model_parameter_array(array.name) else list(array.values)
            )
    elif scheme == "per_array_symmetric_int8":
        for array in arrays:
            if is_model_parameter_array(array.name):
                scale = scale_for_values(array.values)
                scales[array.name] = scale
                dequantized_values[array.name] = quantize_with_scale(array.values, scale)
            else:
                dequantized_values[array.name] = list(array.values)
    elif scheme == "per_layer_group_symmetric_int8":
        names = {array.name for array in arrays}
        missing = sorted(MODEL_ARRAYS - names)
        if missing:
            warnings.append("Missing model arrays for layer grouping: " + ", ".join(missing))
        for group_name, group_arrays in LAYER_GROUPS.items():
            values = [
                value
                for array in arrays
                if array.name in group_arrays
                for value in array.values
            ]
            scales[group_name] = scale_for_values(values)
        for array in arrays:
            group = next((name for name, group_arrays in LAYER_GROUPS.items() if array.name in group_arrays), None)
            if group is None:
                dequantized_values[array.name] = list(array.values)
            else:
                dequantized_values[array.name] = quantize_with_scale(array.values, scales[group])
    else:
        raise ValueError(f"Unsupported quantization scheme: {scheme}")

    shaped = {}
    dimensions_by_name = {array.name: array.dimensions for array in arrays}
    for name, values in dequantized_values.items():
        shaped[name] = reshape(values, dimensions_by_name[name])
    return shaped, scales, warnings


def make_model(text: str, scheme: str | None = None) -> tuple[dict[str, object], dict[str, float], list[str]]:
    defines = parse_defines(text)
    warnings: list[str] = []
    if scheme is None:
        arrays = {array.name: reshape(array.values, array.dimensions) for array in parse_float_arrays(text)}
        scales = {}
    else:
        arrays, scales, warnings = make_dequantized_arrays(text, scheme)
    required = ["SCALER_MIN", "SCALER_SCALE", "W0", "B0", "W1", "B1", "W2", "B2"]
    missing = [name for name in required if name not in arrays]
    if missing:
        raise ValueError("Missing required arrays: " + ", ".join(missing))
    return {"defines": defines, "arrays": arrays}, scales, warnings


def load_replay_rows(paths: list[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in paths:
        rows.extend(read_replay_csv(path))
    if not rows:
        raise ValueError("No valid replay rows found.")
    return rows


def evaluate_scheme(text: str, replay_rows: list[dict[str, object]], scheme: str) -> dict[str, object]:
    float_model, _, _ = make_model(text, None)
    dequant_model, scales, warnings = make_model(text, scheme)
    records: list[dict[str, object]] = []
    for row in replay_rows:
        soc_float = predict(float_model, row["features"])
        soc_dequant = predict(dequant_model, row["features"])
        signed_diff = soc_dequant - soc_float
        record = {
            "abs_diff": abs(signed_diff),
            "signed_diff": signed_diff,
            "dequantized_abs_error_vs_reference": None,
        }
        if row["soc_reference"] is not None:
            record["dequantized_abs_error_vs_reference"] = abs(soc_dequant - row["soc_reference"])
        records.append(record)

    diff_metrics = compute_metrics(records)
    reference_errors = [
        record["dequantized_abs_error_vs_reference"]
        for record in records
        if record["dequantized_abs_error_vs_reference"] is not None
    ]
    model_params = sum(array.parameter_count for array in model_arrays(text))
    return {
        "scheme": scheme,
        "n_samples": diff_metrics["n_samples"],
        "max_abs_diff_float_vs_dequant": diff_metrics["max_abs_diff"],
        "mean_abs_diff_float_vs_dequant": diff_metrics["mean_abs_diff"],
        "rmse_diff_float_vs_dequant": diff_metrics["rmse_diff"],
        "p95_abs_diff_float_vs_dequant": diff_metrics["p95_abs_diff"],
        "max_abs_error_dequant_vs_reference": max(reference_errors) if reference_errors else None,
        "mean_abs_error_dequant_vs_reference": (sum(reference_errors) / len(reference_errors) if reference_errors else None),
        "rmse_dequant_vs_reference": (
            (sum(value * value for value in reference_errors) / len(reference_errors)) ** 0.5
            if reference_errors
            else None
        ),
        "estimated_model_bytes_float32": model_params * 4,
        "estimated_model_bytes_int8": model_params,
        "compression_ratio": 4.0 if model_params else None,
        "n_scales": len(scales),
        "warnings": warnings,
    }


def compare_schemes(text: str, replay_paths: list[Path] | None = None) -> dict[str, object]:
    paths = replay_paths or [path for path in DEFAULT_REPLAY_CSVS if path.exists()]
    if not paths:
        raise ValueError("No replay CSV found.")
    replay_rows = load_replay_rows(paths)
    scheme_results = [evaluate_scheme(text, replay_rows, scheme) for scheme in SCHEMES]
    ranking = sorted(scheme_results, key=lambda item: item["rmse_diff_float_vs_dequant"])
    return {
        "scope": "Comparação offline de esquemas de quantização; não é firmware INT8 embarcado.",
        "replay_csvs": [str(path) for path in paths],
        "schemes": scheme_results,
        "ranking": [item["scheme"] for item in ranking],
        "best_scheme": ranking[0],
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [key for key in payload["schemes"][0].keys() if key != "warnings"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in payload["schemes"]:
            writer.writerow({field: row[field] for field in fields})


def print_summary(payload: dict[str, object], json_path: Path, csv_path: Path) -> None:
    best = payload["best_scheme"]
    print("V8B2 quantization scheme comparison")
    print(payload["scope"])
    print("Ranking by RMSE float vs dequantized:")
    for index, scheme in enumerate(payload["ranking"], start=1):
        print(f"{index}. {scheme}")
    print("Best scheme:")
    for key in (
        "scheme",
        "n_samples",
        "mean_abs_diff_float_vs_dequant",
        "rmse_diff_float_vs_dequant",
        "p95_abs_diff_float_vs_dequant",
        "max_abs_diff_float_vs_dequant",
        "compression_ratio",
        "n_scales",
    ):
        print(f"- {key}: {best[key]}")
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare V8B2 offline weight quantization schemes.")
    parser.add_argument("--header", type=Path, default=DEFAULT_HEADER, help="Canonical float32 header.")
    parser.add_argument("--replay-csv", action="append", type=Path, help="Replay CSV path. Can be repeated.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Ignored local output directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = load_header(args.header)
        payload = compare_schemes(text, args.replay_csv)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    json_path = args.output_dir / "v8b2_quantization_scheme_comparison.json"
    csv_path = args.output_dir / "v8b2_quantization_scheme_comparison.csv"
    write_json(json_path, payload)
    write_csv(csv_path, payload)
    print_summary(payload, json_path, csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
