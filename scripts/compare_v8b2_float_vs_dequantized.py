from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

try:
    from analyze_v8b2_model_footprint import DEFAULT_HEADER, load_header, parse_defines, parse_float_arrays
except ModuleNotFoundError:
    from scripts.analyze_v8b2_model_footprint import DEFAULT_HEADER, load_header, parse_defines, parse_float_arrays


DEFAULT_REPLAY_CSVS = [
    Path("embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv"),
    Path("embedded/handoff_v8b2/replay/canonical_extended_replay_v8b2.csv"),
]
DEFAULT_OUTPUT_DIR = Path("local_runs/quantization_v8b2")
FEATURE_COLUMNS = [
    "voltage_v",
    "temperature_c",
    "current_ma",
    "delta_voltage",
    "delta_temperature",
    "delta_current",
]


def clip_soc(value: float) -> float:
    return max(0.0, min(1.0, value))


def relu(value: float) -> float:
    return value if value > 0.0 else 0.0


def quantize_dequantize_values(values: list[float]) -> list[float]:
    if not values:
        return []
    max_abs = max(abs(value) for value in values)
    scale = max_abs / 127.0 if max_abs != 0.0 else 1.0
    output: list[float] = []
    for value in values:
        quantized = round(value / scale)
        quantized = max(-127, min(127, quantized))
        output.append(quantized * scale)
    return output


def reshape(values: list[float], dimensions: list[int]) -> list:
    if len(dimensions) == 1:
        return list(values)
    if len(dimensions) == 2:
        rows, cols = dimensions
        return [values[index * cols : (index + 1) * cols] for index in range(rows)]
    raise ValueError(f"Unsupported array dimensions: {dimensions}")


def arrays_by_name(text: str, dequantized: bool = False) -> dict[str, list]:
    arrays = {}
    for array in parse_float_arrays(text):
        values = quantize_dequantize_values(array.values) if dequantized and array.name.startswith(("W", "B")) else array.values
        arrays[array.name] = reshape(values, array.dimensions)
    return arrays


def build_model(text: str, dequantized: bool = False) -> dict[str, object]:
    defines = parse_defines(text)
    arrays = arrays_by_name(text, dequantized=dequantized)
    required = ["SCALER_MIN", "SCALER_SCALE", "W0", "B0", "W1", "B1", "W2", "B2"]
    missing = [name for name in required if name not in arrays]
    if missing:
        raise ValueError("Missing required arrays: " + ", ".join(missing))
    for name in ("MLP_INPUT_SIZE", "MLP_L0_SIZE", "MLP_L1_SIZE", "MLP_OUTPUT_SIZE"):
        if name not in defines:
            raise ValueError(f"Missing required define: {name}")
    return {"defines": defines, "arrays": arrays}


def predict(model: dict[str, object], features: list[float]) -> float:
    arrays = model["arrays"]
    defines = model["defines"]
    if len(features) != defines["MLP_INPUT_SIZE"]:
        raise ValueError(f"Expected {defines['MLP_INPUT_SIZE']} features, got {len(features)}")

    scaled = [
        (features[index] - arrays["SCALER_MIN"][index]) * arrays["SCALER_SCALE"][index]
        for index in range(len(features))
    ]

    h0 = []
    for j in range(defines["MLP_L0_SIZE"]):
        acc = arrays["B0"][j]
        for i in range(defines["MLP_INPUT_SIZE"]):
            acc += scaled[i] * arrays["W0"][i][j]
        h0.append(relu(acc))

    h1 = []
    for j in range(defines["MLP_L1_SIZE"]):
        acc = arrays["B1"][j]
        for i in range(defines["MLP_L0_SIZE"]):
            acc += h0[i] * arrays["W1"][i][j]
        h1.append(relu(acc))

    output = arrays["B2"][0]
    for i in range(defines["MLP_L1_SIZE"]):
        output += h1[i] * arrays["W2"][i][0]
    return clip_soc(output)


def read_replay_csv(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"Replay CSV not found: {path}")
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Replay CSV has no header: {path}")
        missing_features = [column for column in FEATURE_COLUMNS if column not in reader.fieldnames]
        if missing_features:
            raise ValueError(f"{path} missing feature columns: {', '.join(missing_features)}")
        for index, row in enumerate(reader, start=1):
            sample_id = row.get("sample_id") or row.get("scenario_id") or f"{path.stem}_{index}"
            mode = row.get("mode") or ("ANOMALY" if "anomaly" in path.stem.lower() else path.stem)
            reference_text = row.get("soc_clipped_reference", "")
            rows.append(
                {
                    "sample_id": sample_id,
                    "mode": mode,
                    "source_file": str(path),
                    "features": [float(row[column]) for column in FEATURE_COLUMNS],
                    "soc_reference": float(reference_text) if reference_text != "" else None,
                }
            )
    return rows


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percent
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def compute_metrics(records: list[dict[str, object]]) -> dict[str, object]:
    abs_diff = [record["abs_diff"] for record in records]
    signed_diff = [record["signed_diff"] for record in records]
    return {
        "n_samples": len(records),
        "max_abs_diff": max(abs_diff) if abs_diff else None,
        "mean_abs_diff": statistics.fmean(abs_diff) if abs_diff else None,
        "rmse_diff": math.sqrt(statistics.fmean([value * value for value in signed_diff])) if signed_diff else None,
        "p95_abs_diff": percentile(abs_diff, 0.95),
        "max_signed_diff": max(signed_diff) if signed_diff else None,
        "mean_signed_diff": statistics.fmean(signed_diff) if signed_diff else None,
    }


def compare_predictions(header_text: str, replay_paths: list[Path]) -> tuple[list[dict[str, object]], dict[str, object]]:
    float_model = build_model(header_text, dequantized=False)
    dequantized_model = build_model(header_text, dequantized=True)
    replay_rows: list[dict[str, object]] = []
    for path in replay_paths:
        replay_rows.extend(read_replay_csv(path))
    if not replay_rows:
        raise ValueError("No valid replay rows found.")

    records: list[dict[str, object]] = []
    for row in replay_rows:
        soc_float = predict(float_model, row["features"])
        soc_dequantized = predict(dequantized_model, row["features"])
        signed_diff = soc_dequantized - soc_float
        record = {
            "sample_id": row["sample_id"],
            "mode": row["mode"],
            "source_file": row["source_file"],
            "soc_float": soc_float,
            "soc_dequantized": soc_dequantized,
            "abs_diff": abs(signed_diff),
            "signed_diff": signed_diff,
            "soc_reference": row["soc_reference"],
            "float_abs_error_vs_reference": None,
            "dequantized_abs_error_vs_reference": None,
        }
        if row["soc_reference"] is not None:
            record["float_abs_error_vs_reference"] = abs(soc_float - row["soc_reference"])
            record["dequantized_abs_error_vs_reference"] = abs(soc_dequantized - row["soc_reference"])
        records.append(record)

    by_source = {}
    for source in sorted({record["source_file"] for record in records}):
        by_source[source] = compute_metrics([record for record in records if record["source_file"] == source])
    summary = {
        "scope": "Comparação offline de inferência com pesos dequantizados; não é firmware INT8 embarcado.",
        "global": compute_metrics(records),
        "by_source": by_source,
        "reference_available": any(record["soc_reference"] is not None for record in records),
    }
    return records, summary


def write_predictions_csv(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "mode",
        "source_file",
        "soc_float",
        "soc_dequantized",
        "abs_diff",
        "signed_diff",
        "soc_reference",
        "float_abs_error_vs_reference",
        "dequantized_abs_error_vs_reference",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def write_json(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_summary(summary: dict[str, object], csv_path: Path, json_path: Path) -> None:
    metrics = summary["global"]
    print("V8B2 float vs dequantized inference")
    print(summary["scope"])
    print(f"n_samples: {metrics['n_samples']}")
    print(f"max_abs_diff: {metrics['max_abs_diff']}")
    print(f"mean_abs_diff: {metrics['mean_abs_diff']}")
    print(f"rmse_diff: {metrics['rmse_diff']}")
    print(f"p95_abs_diff: {metrics['p95_abs_diff']}")
    print(f"max_signed_diff: {metrics['max_signed_diff']}")
    print(f"mean_signed_diff: {metrics['mean_signed_diff']}")
    print(f"reference_available: {summary['reference_available']}")
    print(f"CSV predictions: {csv_path}")
    print(f"JSON summary: {json_path}")


def default_replay_paths() -> list[Path]:
    return [path for path in DEFAULT_REPLAY_CSVS if path.exists()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare V8B2 float32 MLP with dequantized-weight simulation.")
    parser.add_argument("--header", type=Path, default=DEFAULT_HEADER, help="Canonical C header.")
    parser.add_argument("--replay-csv", action="append", type=Path, help="Replay CSV path. Can be repeated.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Ignored local output directory.")
    parser.add_argument("--json", type=Path, help="Optional JSON summary path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    replay_paths = args.replay_csv or default_replay_paths()
    if not replay_paths:
        print("No replay CSV found. Pass --replay-csv explicitly.", file=sys.stderr)
        return 1
    try:
        header_text = load_header(args.header)
        records, summary = compare_predictions(header_text, replay_paths)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    csv_path = args.output_dir / "v8b2_float_vs_dequantized_predictions.csv"
    json_path = args.json or args.output_dir / "v8b2_float_vs_dequantized_summary.json"
    write_predictions_csv(csv_path, records)
    write_json(json_path, summary)
    print_summary(summary, csv_path, json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
