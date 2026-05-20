from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

try:
    from compare_v8b2_float_vs_dequantized import (
        FEATURE_COLUMNS,
        build_model,
        load_header,
        predict,
        read_replay_csv,
    )
except ModuleNotFoundError:
    from scripts.compare_v8b2_float_vs_dequantized import (
        FEATURE_COLUMNS,
        build_model,
        load_header,
        predict,
        read_replay_csv,
    )


DEFAULT_BASELINE_HEADER = Path("embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h")
DEFAULT_CANDIDATE_HEADER = Path("embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model.h")
DEFAULT_REPLAY_CSVS = [
    Path("embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv"),
    Path("embedded/handoff_v8b2/replay/canonical_extended_replay_v8b2.csv"),
]
DEFAULT_OUTPUT_DIR = Path("reports/v8c_quant_benchmark")
CONSERVATIVE_MAX_ABS_DIFF_LIMIT = 0.01
INT8_SCALE_PATTERN = re.compile(
    r"static\s+const\s+float\s+([A-Za-z_][A-Za-z0-9_]*)_INT8_SCALE\s*=\s*([-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?f?)\s*;"
)
INT8_ARRAY_PATTERN = re.compile(
    r"static\s+const\s+int8_t\s+([A-Za-z_][A-Za-z0-9_]*)_Q\s*((?:\[[0-9]+\])+)\s*=\s*\{(.*?)\};",
    re.DOTALL,
)
FLOAT_ARRAY_PATTERN = re.compile(
    r"static\s+const\s+float\s+([A-Za-z_][A-Za-z0-9_]*)\s*((?:\[[0-9]+\])+)\s*=\s*\{(.*?)\};",
    re.DOTALL,
)
NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?f?")


@dataclass(frozen=True)
class CandidateArray:
    name: str
    dimensions: list[int]
    values: list[int]
    scale: float


def finite(value: float) -> bool:
    return math.isfinite(value)


def count_nonfinite(values: list[float]) -> int:
    return sum(1 for value in values if not finite(value))


def metric_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mae": None, "rmse": None, "max_abs_diff": None}
    return {
        "n": len(values),
        "mae": statistics.fmean(abs(value) for value in values),
        "rmse": math.sqrt(statistics.fmean(value * value for value in values)),
        "max_abs_diff": max(abs(value) for value in values),
    }


def soc_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "max": None, "nan_inf_count": 0}
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "nan_inf_count": count_nonfinite(values),
    }


def load_rows(replay_paths: list[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in replay_paths:
        rows.extend(read_replay_csv(path))
    return rows


def parse_number(value: str) -> float:
    return float(value.rstrip("fF"))


def parse_dimensions(dimensions_text: str) -> list[int]:
    return [int(value) for value in re.findall(r"\[([0-9]+)\]", dimensions_text)]


def reshape(values: list[float], dimensions: list[int]) -> list:
    if len(dimensions) == 1:
        return list(values)
    if len(dimensions) == 2:
        rows, cols = dimensions
        return [values[index * cols : (index + 1) * cols] for index in range(rows)]
    raise ValueError(f"Unsupported dimensions: {dimensions}")


def parse_float_arrays_from_candidate(text: str) -> dict[str, list]:
    arrays: dict[str, list] = {}
    for name, dimensions_text, body in FLOAT_ARRAY_PATTERN.findall(text):
        dimensions = parse_dimensions(dimensions_text)
        values = [parse_number(match.group(0)) for match in NUMBER_PATTERN.finditer(body)]
        arrays[name] = reshape(values, dimensions)
    return arrays


def parse_int8_candidate_arrays(text: str) -> dict[str, CandidateArray]:
    scales = {name: parse_number(value) for name, value in INT8_SCALE_PATTERN.findall(text)}
    arrays: dict[str, CandidateArray] = {}
    for name, dimensions_text, body in INT8_ARRAY_PATTERN.findall(text):
        if name not in scales:
            raise ValueError(f"Candidate array {name}_Q has no {name}_INT8_SCALE")
        dimensions = parse_dimensions(dimensions_text)
        values = [int(parse_number(match.group(0))) for match in NUMBER_PATTERN.finditer(body)]
        expected = 1
        for dimension in dimensions:
            expected *= dimension
        if expected != len(values):
            raise ValueError(f"Candidate array {name}_Q expected {expected} values, parsed {len(values)}")
        arrays[name] = CandidateArray(name=name, dimensions=dimensions, values=values, scale=scales[name])
    return arrays


def build_int8_candidate_model(candidate_header: Path) -> dict[str, object]:
    text = load_header(candidate_header)
    float_arrays = parse_float_arrays_from_candidate(text)
    int8_arrays = parse_int8_candidate_arrays(text)
    required_float = ["SCALER_MIN", "SCALER_SCALE"]
    required_int8 = ["W0", "B0", "W1", "B1", "W2", "B2"]
    missing_float = [name for name in required_float if name not in float_arrays]
    missing_int8 = [name for name in required_int8 if name not in int8_arrays]
    if missing_float or missing_int8:
        missing = missing_float + [f"{name}_Q" for name in missing_int8]
        raise ValueError("Candidate header missing required arrays: " + ", ".join(missing))
    return {"float_arrays": float_arrays, "int8_arrays": int8_arrays}


def dequantize(array: CandidateArray) -> list:
    return reshape([value * array.scale for value in array.values], array.dimensions)


def relu(value: float) -> float:
    return value if value > 0.0 else 0.0


def clip_soc(value: float) -> float:
    return max(0.0, min(1.0, value))


def predict_int8_candidate(model: dict[str, object], features: list[float]) -> float:
    float_arrays = model["float_arrays"]
    int8_arrays = model["int8_arrays"]
    scaler_min = float_arrays["SCALER_MIN"]
    scaler_scale = float_arrays["SCALER_SCALE"]
    if len(features) != len(scaler_min):
        raise ValueError(f"Expected {len(scaler_min)} features, got {len(features)}")

    scaled = [(features[index] - scaler_min[index]) * scaler_scale[index] for index in range(len(features))]
    w0 = dequantize(int8_arrays["W0"])
    b0 = dequantize(int8_arrays["B0"])
    w1 = dequantize(int8_arrays["W1"])
    b1 = dequantize(int8_arrays["B1"])
    w2 = dequantize(int8_arrays["W2"])
    b2 = dequantize(int8_arrays["B2"])

    h0 = []
    for j in range(len(b0)):
        acc = b0[j]
        for i in range(len(scaled)):
            acc += scaled[i] * w0[i][j]
        h0.append(relu(acc))

    h1 = []
    for j in range(len(b1)):
        acc = b1[j]
        for i in range(len(h0)):
            acc += h0[i] * w1[i][j]
        h1.append(relu(acc))

    output = b2[0]
    for i in range(len(h1)):
        output += h1[i] * w2[i][0]
    return clip_soc(output)


def baseline_records(baseline_header: Path, replay_paths: list[Path]) -> tuple[list[dict[str, object]], dict[str, object]]:
    model = build_model(load_header(baseline_header), dequantized=False)
    rows = load_rows(replay_paths)
    records: list[dict[str, object]] = []
    baseline_errors: list[float] = []
    for row in rows:
        soc = predict(model, row["features"])
        reference = row["soc_reference"]
        error = None if reference is None else soc - float(reference)
        if error is not None:
            baseline_errors.append(error)
        records.append(
            {
                "sample_id": row["sample_id"],
                "mode": row["mode"],
                "source_file": row["source_file"],
                "soc_float_baseline": soc,
                "soc_candidate": None,
                "candidate_minus_float": None,
                "soc_reference": reference,
                "float_error_vs_reference": error,
                "candidate_error_vs_reference": None,
                "status": "BASELINE_ONLY",
            }
        )
    summary = {
        "baseline_header": baseline_header.as_posix(),
        "feature_order": FEATURE_COLUMNS,
        "baseline_status": "BASELINE_REPORT_GENERATED",
        "baseline_error_vs_reference": metric_summary(baseline_errors),
        "n_records": len(records),
        "soc_final_clip_policy": "clip only final SOC to [0, 1]",
        "scaled_feature_clip_policy": "do not clip scaled features",
        "all_outputs_finite": all(finite(float(record["soc_float_baseline"])) for record in records),
        "all_soc_in_unit_interval": all(0.0 <= float(record["soc_float_baseline"]) <= 1.0 for record in records),
        "baseline_soc_summary": soc_summary([float(record["soc_float_baseline"]) for record in records]),
    }
    return records, summary


def compare_candidate(
    baseline_header: Path,
    candidate_header: Path,
    replay_paths: list[Path],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    records, summary = baseline_records(baseline_header, replay_paths)
    if not candidate_header.exists():
        summary.update(
            {
                "candidate_header": candidate_header.as_posix(),
                "candidate_status": "CANDIDATE_NOT_AVAILABLE",
                "candidate_error_vs_reference": metric_summary([]),
                "candidate_diff_vs_float": metric_summary([]),
                "candidate_soc_summary": soc_summary([]),
                "candidate_nan_inf_count": 0,
            }
        )
        return records, summary

    candidate_model = build_int8_candidate_model(candidate_header)
    rows = load_rows(replay_paths)
    diffs: list[float] = []
    candidate_errors: list[float] = []
    candidate_socs: list[float] = []
    for record, row in zip(records, rows):
        candidate_soc = predict_int8_candidate(candidate_model, row["features"])
        diff = candidate_soc - float(record["soc_float_baseline"])
        candidate_error = None if row["soc_reference"] is None else candidate_soc - float(row["soc_reference"])
        diffs.append(diff)
        candidate_socs.append(candidate_soc)
        if candidate_error is not None:
            candidate_errors.append(candidate_error)
        record["soc_candidate"] = candidate_soc
        record["candidate_minus_float"] = diff
        record["candidate_error_vs_reference"] = candidate_error
        record["status"] = "CANDIDATE_COMPARED"

    summary.update(
        {
            "candidate_header": candidate_header.as_posix(),
            "candidate_status": "CANDIDATE_AVAILABLE",
            "candidate_scheme": "per_array_symmetric_int8_dequantized_forward",
            "candidate_error_vs_reference": metric_summary(candidate_errors),
            "candidate_diff_vs_float": metric_summary(diffs),
            "candidate_soc_summary": soc_summary(candidate_socs),
            "candidate_nan_inf_count": count_nonfinite(candidate_socs + diffs + candidate_errors),
            "conservative_max_abs_diff_limit": CONSERVATIVE_MAX_ABS_DIFF_LIMIT,
            "candidate_within_conservative_limit": (
                metric_summary(diffs)["max_abs_diff"] is not None
                and metric_summary(diffs)["max_abs_diff"] <= CONSERVATIVE_MAX_ABS_DIFF_LIMIT
            ),
            "all_outputs_finite": all(
                finite(float(record["soc_float_baseline"]))
                and (record["soc_candidate"] is None or finite(float(record["soc_candidate"])))
                for record in records
            ),
            "all_soc_in_unit_interval": all(
                0.0 <= float(record["soc_float_baseline"]) <= 1.0
                and (record["soc_candidate"] is None or 0.0 <= float(record["soc_candidate"]) <= 1.0)
                for record in records
            ),
        }
    )
    return records, summary


def write_records_csv(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "mode",
        "source_file",
        "soc_float_baseline",
        "soc_candidate",
        "candidate_minus_float",
        "soc_reference",
        "float_error_vs_reference",
        "candidate_error_vs_reference",
        "candidate_abs_diff_vs_float",
        "candidate_abs_error_vs_reference",
        "status",
    ]
    for record in records:
        diff = record.get("candidate_minus_float")
        err = record.get("candidate_error_vs_reference")
        record["candidate_abs_diff_vs_float"] = None if diff is None else abs(float(diff))
        record["candidate_abs_error_vs_reference"] = None if err is None else abs(float(err))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare V8C baseline float with an optional candidate model.")
    parser.add_argument("--baseline-header", type=Path, default=DEFAULT_BASELINE_HEADER)
    parser.add_argument("--candidate-header", type=Path, default=DEFAULT_CANDIDATE_HEADER)
    parser.add_argument("--replay-csv", type=Path, action="append")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--csv", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    replay_paths = args.replay_csv or DEFAULT_REPLAY_CSVS
    records, summary = compare_candidate(args.baseline_header, args.candidate_header, replay_paths)
    csv_path = args.csv or args.output_dir / "v8c_python_float_vs_candidate_predictions.csv"
    json_path = args.json or args.output_dir / "v8c_python_float_vs_candidate_summary.json"
    write_records_csv(csv_path, records)
    write_json(json_path, summary)
    print(f"candidate_status: {summary['candidate_status']}")
    print(f"records_csv: {csv_path}")
    print(f"summary_json: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
