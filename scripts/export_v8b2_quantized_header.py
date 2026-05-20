from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from analyze_v8b2_model_footprint import DEFAULT_HEADER, load_header, parse_defines, parse_float_arrays
    from compare_v8b2_quantization_schemes import SCHEMES, scale_for_values
except ModuleNotFoundError:
    from scripts.analyze_v8b2_model_footprint import DEFAULT_HEADER, load_header, parse_defines, parse_float_arrays
    from scripts.compare_v8b2_quantization_schemes import SCHEMES, scale_for_values


DEFAULT_OUTPUT = Path("embedded/quantization/canonical_model_weights_v8b2_int8_candidate.h")
DEFAULT_MANIFEST = Path("embedded/quantization/V8B2_INT8_CANDIDATE_MANIFEST.json")
MODEL_ARRAYS = {"W0", "B0", "W1", "B1", "W2", "B2"}
FEATURE_ORDER = [
    "voltage_v",
    "temperature_c",
    "current_ma",
    "delta_voltage",
    "delta_temperature",
    "delta_current",
]


def quantize_values(values: list[float], scale: float) -> list[int]:
    quantized: list[int] = []
    for value in values:
        q_value = round(value / scale)
        q_value = max(-127, min(127, q_value))
        quantized.append(q_value)
    return quantized


def scales_for_scheme(text: str, scheme: str) -> dict[str, float]:
    arrays = parse_float_arrays(text)
    by_name = {array.name: array for array in arrays}
    if scheme == "per_array_symmetric_int8":
        return {name: scale_for_values(by_name[name].values) for name in sorted(MODEL_ARRAYS)}
    if scheme == "global_symmetric_int8":
        values = [value for name in MODEL_ARRAYS for value in by_name[name].values]
        scale = scale_for_values(values)
        return {name: scale for name in sorted(MODEL_ARRAYS)}
    if scheme == "per_layer_group_symmetric_int8":
        groups = {"L0": ["W0", "B0"], "L1": ["W1", "B1"], "L2": ["W2", "B2"]}
        group_scales = {}
        for group, names in groups.items():
            group_scales[group] = scale_for_values([value for name in names for value in by_name[name].values])
        return {
            "B0": group_scales["L0"],
            "W0": group_scales["L0"],
            "B1": group_scales["L1"],
            "W1": group_scales["L1"],
            "B2": group_scales["L2"],
            "W2": group_scales["L2"],
        }
    raise ValueError(f"Unsupported scheme: {scheme}")


def c_initializer_int(values: list[int], dimensions: list[int], indent: str = "  ") -> str:
    if len(dimensions) == 1:
        return "{ " + ", ".join(str(value) for value in values) + " }"
    if len(dimensions) == 2:
        rows, cols = dimensions
        lines = ["{"]
        for row in range(rows):
            chunk = values[row * cols : (row + 1) * cols]
            suffix = "," if row < rows - 1 else ""
            lines.append(indent + "{ " + ", ".join(str(value) for value in chunk) + " }" + suffix)
        lines.append("}")
        return "\n".join(lines)
    raise ValueError(f"Unsupported dimensions: {dimensions}")


def c_initializer_float(values: list[float]) -> str:
    return "{ " + ", ".join(c_float(value) for value in values) + " }"


def c_float(value: float) -> str:
    text = f"{value:.10g}"
    if "e" not in text.lower() and "." not in text:
        text += ".0"
    return text + "f"


def dims_suffix(dimensions: list[int]) -> str:
    return "".join(f"[{dimension}]" for dimension in dimensions)


def render_header(text: str, scheme: str) -> str:
    defines = parse_defines(text)
    arrays = parse_float_arrays(text)
    by_name = {array.name: array for array in arrays}
    missing = sorted(MODEL_ARRAYS - set(by_name))
    if missing:
        raise ValueError("Missing model arrays: " + ", ".join(missing))
    scales = scales_for_scheme(text, scheme)

    lines = [
        "/*",
        " * SOC-EDGE V8B2 INT8 candidate header.",
        " * Header candidato para experimento de quantizacao.",
        " * Nao representa firmware INT8 validado.",
        " * Baseline canonico permanece float32 V8B2.",
        " */",
        "#ifndef CANONICAL_MODEL_WEIGHTS_V8B2_INT8_CANDIDATE_H",
        "#define CANONICAL_MODEL_WEIGHTS_V8B2_INT8_CANDIDATE_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define V8B2_INT8_CANDIDATE_SCHEME_{scheme.upper()} 1",
    ]
    for name in ("MLP_INPUT_SIZE", "MLP_L0_SIZE", "MLP_L1_SIZE", "MLP_OUTPUT_SIZE"):
        lines.append(f"#define {name} {defines[name]}")
    lines.extend(
        [
            "",
            "/* Feature order: voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current */",
            "/* Scaler rule: x_scaled[i] = (x[i] - SCALER_MIN[i]) * SCALER_SCALE[i]. Do not clip scaled features. */",
            "/* Output rule: clip only final SOC output to [0, 1]. */",
            "",
            f"static const float SCALER_MIN[6] = {c_initializer_float(by_name['SCALER_MIN'].values)};",
            f"static const float SCALER_SCALE[6] = {c_initializer_float(by_name['SCALER_SCALE'].values)};",
            "",
        ]
    )

    for name in ("W0", "B0", "W1", "B1", "W2", "B2"):
        array = by_name[name]
        scale = scales[name]
        quantized = quantize_values(array.values, scale)
        lines.append(f"static const float {name}_INT8_SCALE = {c_float(scale)};")
        lines.append(f"static const int8_t {name}_Q{dims_suffix(array.dimensions)} = {c_initializer_int(quantized, array.dimensions)};")
        lines.append("")

    lines.append("#endif")
    lines.append("")
    return "\n".join(lines)


def write_manifest(path: Path, header_output: Path, scheme: str) -> None:
    manifest = {
        "candidate_name": "SOC-EDGE V8B2 INT8 candidate header",
        "source_float_header": "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h",
        "source_package_stage": "V8B2",
        "scheme": scheme,
        "status": "offline quantization candidate",
        "validation_scope": "offline weight quantization and dequantized inference comparison",
        "claim_limits": [
            "no embedded INT8 validation",
            "no latency claim",
            "no production claim",
            "no field validation",
            "no physical sensor validation",
        ],
        "generated_header": str(header_output).replace("\\", "/"),
        "feature_order": FEATURE_ORDER,
        "output_rule": "Clip only final SOC output to [0, 1].",
        "notes": "Candidate text header for future firmware experiments; float32 V8B2 remains canonical baseline.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export V8B2 quantized candidate C header.")
    parser.add_argument("--scheme", default="per_array_symmetric_int8", choices=SCHEMES)
    parser.add_argument("--header", type=Path, default=DEFAULT_HEADER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = load_header(args.header)
        rendered = render_header(text, args.scheme)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    write_manifest(args.manifest, args.output, args.scheme)
    print("V8B2 INT8 candidate header exported")
    print("Header candidato para experimento de quantizacao. Nao representa firmware INT8 validado.")
    print(f"scheme: {args.scheme}")
    print(f"header: {args.output}")
    print(f"manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
