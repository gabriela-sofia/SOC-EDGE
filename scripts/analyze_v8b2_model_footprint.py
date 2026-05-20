from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_HEADER = Path("embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h")
DEFINE_PATTERN = re.compile(r"^\s*#define\s+(MLP_[A-Z0-9_]+)\s+([0-9]+)\s*$", re.MULTILINE)
ARRAY_PATTERN = re.compile(
    r"static\s+const\s+float\s+([A-Za-z_][A-Za-z0-9_]*)\s*((?:\[[0-9]+\])+)\s*=\s*\{(.*?)\};",
    re.DOTALL,
)
FLOAT_PATTERN = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?f?")


@dataclass(frozen=True)
class FloatArray:
    name: str
    dimensions: list[int]
    values: list[float]

    @property
    def parameter_count(self) -> int:
        return len(self.values)


def load_header(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Header not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_defines(text: str) -> dict[str, int]:
    return {name: int(value) for name, value in DEFINE_PATTERN.findall(text)}


def parse_float_arrays(text: str) -> list[FloatArray]:
    arrays: list[FloatArray] = []
    for name, dimensions_text, body in ARRAY_PATTERN.findall(text):
        dimensions = [int(value) for value in re.findall(r"\[([0-9]+)\]", dimensions_text)]
        values = [float(match.group(0).rstrip("fF")) for match in FLOAT_PATTERN.finditer(body)]
        arrays.append(FloatArray(name=name, dimensions=dimensions, values=values))
    return arrays


def expected_count(dimensions: list[int]) -> int:
    total = 1
    for dimension in dimensions:
        total *= dimension
    return total


def is_model_parameter_array(name: str) -> bool:
    return name.startswith(("W", "B"))


def analyze_footprint(text: str) -> dict[str, object]:
    defines = parse_defines(text)
    arrays = parse_float_arrays(text)
    warnings: list[str] = []
    per_array: dict[str, dict[str, object]] = {}

    for array in arrays:
        expected = expected_count(array.dimensions)
        if expected != array.parameter_count:
            warnings.append(
                f"{array.name}: expected {expected} values from dimensions, parsed {array.parameter_count}"
            )
        per_array[array.name] = {
            "dimensions": array.dimensions,
            "parameter_count": array.parameter_count,
            "is_model_parameter": is_model_parameter_array(array.name),
            "float32_bytes": array.parameter_count * 4,
            "int8_bytes": array.parameter_count,
        }

    missing_defines = [
        name
        for name in ("MLP_INPUT_SIZE", "MLP_L0_SIZE", "MLP_L1_SIZE", "MLP_OUTPUT_SIZE")
        if name not in defines
    ]
    if missing_defines:
        warnings.append("Missing expected defines: " + ", ".join(missing_defines))

    total_parameters = sum(array.parameter_count for array in arrays)
    model_parameters = sum(array.parameter_count for array in arrays if is_model_parameter_array(array.name))
    float32_bytes = total_parameters * 4
    int8_bytes = total_parameters
    model_float32_bytes = model_parameters * 4
    model_int8_bytes = model_parameters

    return {
        "header_scope": "SOC V8B2 canonical float32 model footprint analysis",
        "defines": defines,
        "arrays": per_array,
        "number_of_arrays_parsed": len(arrays),
        "total_float_parameters": total_parameters,
        "model_float_parameters": model_parameters,
        "estimated_float32_bytes": float32_bytes,
        "estimated_int8_bytes": int8_bytes,
        "estimated_model_float32_bytes": model_float32_bytes,
        "estimated_model_int8_bytes": model_int8_bytes,
        "theoretical_compression_ratio": float32_bytes / int8_bytes if int8_bytes else None,
        "theoretical_model_compression_ratio": (
            model_float32_bytes / model_int8_bytes if model_int8_bytes else None
        ),
        "warnings": warnings,
        "claim_limit": "Footprint estimate only; this is not validated INT8 embedded firmware.",
    }


def write_json_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_report(report: dict[str, object]) -> None:
    print("V8B2 model footprint")
    print(f"Arrays parsed: {report['number_of_arrays_parsed']}")
    print(f"Total float parameters: {report['total_float_parameters']}")
    print(f"Model float parameters: {report['model_float_parameters']}")
    print(f"Estimated float32 bytes: {report['estimated_float32_bytes']}")
    print(f"Estimated int8 bytes: {report['estimated_int8_bytes']}")
    print(f"Estimated model float32 bytes: {report['estimated_model_float32_bytes']}")
    print(f"Estimated model int8 bytes: {report['estimated_model_int8_bytes']}")
    print(f"Theoretical compression ratio: {report['theoretical_compression_ratio']}")
    print(f"Theoretical model compression ratio: {report['theoretical_model_compression_ratio']}")
    print("Defines:")
    for name in ("MLP_INPUT_SIZE", "MLP_L0_SIZE", "MLP_L1_SIZE", "MLP_OUTPUT_SIZE"):
        print(f"- {name}: {report['defines'].get(name, 'WARN: not found')}")
    print("Arrays:")
    for name, metrics in report["arrays"].items():
        dims = "x".join(str(value) for value in metrics["dimensions"])
        print(f"- {name}: dims={dims}, params={metrics['parameter_count']}, float32_bytes={metrics['float32_bytes']}, int8_bytes={metrics['int8_bytes']}")
    if report["warnings"]:
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"- {warning}")
    print(report["claim_limit"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze V8B2 canonical model header footprint.")
    parser.add_argument("--header", type=Path, default=DEFAULT_HEADER, help="Canonical C header with float arrays.")
    parser.add_argument("--json", type=Path, help="Optional JSON report path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = load_header(args.header)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report = analyze_footprint(text)
    print_report(report)
    if args.json:
        write_json_report(args.json, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
