from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

try:
    from analyze_v8b2_model_footprint import (
        DEFAULT_HEADER,
        is_model_parameter_array,
        load_header,
        parse_float_arrays,
    )
except ModuleNotFoundError:
    from scripts.analyze_v8b2_model_footprint import (
        DEFAULT_HEADER,
        is_model_parameter_array,
        load_header,
        parse_float_arrays,
    )


DEFAULT_OUTPUT_DIR = Path("local_runs/quantization_v8b2")


def quantize_symmetric_int8(values: list[float]) -> dict[str, object]:
    if not values:
        return {
            "n": 0,
            "min": None,
            "max": None,
            "mean": None,
            "max_abs": None,
            "scale": None,
            "max_abs_error": None,
            "mean_abs_error": None,
            "rmse": None,
        }

    max_abs = max(abs(value) for value in values)
    scale = max_abs / 127.0 if max_abs != 0 else 1.0
    abs_errors: list[float] = []
    squared_errors: list[float] = []

    for value in values:
        quantized = round(value / scale)
        quantized = max(-127, min(127, quantized))
        dequantized = quantized * scale
        error = value - dequantized
        abs_errors.append(abs(error))
        squared_errors.append(error * error)

    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "max_abs": max_abs,
        "scale": scale,
        "max_abs_error": max(abs_errors),
        "mean_abs_error": statistics.fmean(abs_errors),
        "rmse": math.sqrt(statistics.fmean(squared_errors)),
    }


def simulate_quantization(text: str) -> dict[str, object]:
    arrays = parse_float_arrays(text)
    per_array = {}
    for array in arrays:
        metrics = quantize_symmetric_int8(array.values)
        metrics["is_model_parameter"] = is_model_parameter_array(array.name)
        per_array[array.name] = metrics
    model_values = [
        value
        for array in arrays
        if is_model_parameter_array(array.name)
        for value in array.values
    ]
    return {
        "scope": "simulacao de quantizacao/dequantizacao de pesos; nao e validacao INT8 embarcada",
        "quantization_rule": "symmetric per-tensor int8, q=round(x/scale), clip [-127,127], x_dequant=q*scale",
        "array_count": len(arrays),
        "total_values": sum(len(array.values) for array in arrays),
        "model_parameter_values": len(model_values),
        "global_model_parameters": quantize_symmetric_int8(model_values),
        "arrays": per_array,
    }


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_summary(report: dict[str, object], output_path: Path) -> None:
    global_metrics = report["global_model_parameters"]
    print("V8B2 weight quantization simulation")
    print(report["scope"])
    print(f"Arrays parsed: {report['array_count']}")
    print(f"Total values: {report['total_values']}")
    print(f"Model parameter values: {report['model_parameter_values']}")
    print(f"Model max_abs: {global_metrics['max_abs']}")
    print(f"Model scale: {global_metrics['scale']}")
    print(f"Model max_abs_error: {global_metrics['max_abs_error']}")
    print(f"Model mean_abs_error: {global_metrics['mean_abs_error']}")
    print(f"Model rmse: {global_metrics['rmse']}")
    print(f"JSON report: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate V8B2 per-tensor int8 weight quantization.")
    parser.add_argument("--header", type=Path, default=DEFAULT_HEADER, help="Canonical C header with float arrays.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Ignored local output directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = load_header(args.header)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report = simulate_quantization(text)
    output_path = args.output_dir / "v8b2_weight_quantization_report.json"
    write_report(output_path, report)
    print_summary(report, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
