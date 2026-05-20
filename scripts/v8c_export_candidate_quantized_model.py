from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from analyze_v8b2_model_footprint import DEFAULT_HEADER, load_header, parse_defines, parse_float_arrays
except ModuleNotFoundError:
    from scripts.analyze_v8b2_model_footprint import DEFAULT_HEADER, load_header, parse_defines, parse_float_arrays


DEFAULT_OUTPUT = Path("embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model.h")
DEFAULT_README = Path("embedded/handoff_v8c_quant_benchmark/include/README_candidate_quantized.md")
MODEL_ARRAYS = {"W0", "B0", "W1", "B1", "W2", "B2"}
FEATURE_ORDER = [
    "voltage_v",
    "temperature_c",
    "current_ma",
    "delta_voltage",
    "delta_temperature",
    "delta_current",
]


def c_float(value: float) -> str:
    text = f"{value:.10g}"
    if "e" not in text.lower() and "." not in text:
        text += ".0"
    return text + "f"


def c_initializer_float(values: list[float]) -> str:
    return "{ " + ", ".join(c_float(value) for value in values) + " }"


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


def dims_suffix(dimensions: list[int]) -> str:
    return "".join(f"[{dimension}]" for dimension in dimensions)


def scale_for_values(values: list[float]) -> float:
    max_abs = max(abs(value) for value in values) if values else 0.0
    return max_abs / 127.0 if max_abs else 1.0


def quantize_values(values: list[float], scale: float) -> list[int]:
    quantized: list[int] = []
    for value in values:
        q_value = round(value / scale)
        quantized.append(max(-127, min(127, q_value)))
    return quantized


def render_header(source_text: str) -> str:
    defines = parse_defines(source_text)
    arrays = {array.name: array for array in parse_float_arrays(source_text)}
    missing = sorted((MODEL_ARRAYS | {"SCALER_MIN", "SCALER_SCALE"}) - set(arrays))
    if missing:
        raise ValueError("Missing arrays in baseline header: " + ", ".join(missing))
    for name in ("MLP_INPUT_SIZE", "MLP_L0_SIZE", "MLP_L1_SIZE", "MLP_OUTPUT_SIZE"):
        if name not in defines:
            raise ValueError(f"Missing define in baseline header: {name}")

    lines = [
        "/*",
        " * SOC-EDGE V8C experimental INT8 candidate.",
        " * Source: embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h",
        " * Quantization: deterministic per-array symmetric INT8 for weights and biases.",
        " * Scaler remains float and follows sklearn MinMaxScaler semantics.",
        " * Scaled features are not clipped; only final SOC is clipped to [0, 1].",
        " * Experimental candidate only; baseline V8B2 float remains canonical.",
        " */",
        "#ifndef SOC_EDGE_V8C_CANDIDATE_QUANTIZED_MODEL_H",
        "#define SOC_EDGE_V8C_CANDIDATE_QUANTIZED_MODEL_H",
        "",
        "#include <math.h>",
        "#include <stdint.h>",
        "",
        "#define V8C_CANDIDATE_QUANT_SCHEME_PER_ARRAY_SYMMETRIC_INT8 1",
    ]
    for name in ("MLP_INPUT_SIZE", "MLP_L0_SIZE", "MLP_L1_SIZE", "MLP_OUTPUT_SIZE"):
        lines.append(f"#define {name} {defines[name]}")
    lines.extend(
        [
            "#define V8C_CANDIDATE_PARAMETER_COUNT 2561",
            "",
            "/* Feature order: voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current */",
            "/* Units: voltage_v V, temperature_c C, current_ma mA, delta_voltage V, delta_temperature C, delta_current mA */",
            "/* Scaler: x_scaled[i] = (x[i] - SCALER_MIN[i]) * SCALER_SCALE[i]; do not clip scaled features. */",
            "/* Output: clip only final SOC to [0, 1]. */",
            "",
            f"static const float SCALER_MIN[6] = {c_initializer_float(arrays['SCALER_MIN'].values)};",
            f"static const float SCALER_SCALE[6] = {c_initializer_float(arrays['SCALER_SCALE'].values)};",
            "",
        ]
    )

    for name in ("W0", "B0", "W1", "B1", "W2", "B2"):
        array = arrays[name]
        scale = scale_for_values(array.values)
        quantized = quantize_values(array.values, scale)
        lines.append(f"static const float {name}_INT8_SCALE = {c_float(scale)};")
        lines.append(f"static const int8_t {name}_Q{dims_suffix(array.dimensions)} = {c_initializer_int(quantized, array.dimensions)};")
        lines.append("")

    lines.extend(
        [
            "static inline float v8c_dequant_int8(int8_t value, float scale) {",
            "  return ((float)value) * scale;",
            "}",
            "",
            "static inline float candidate_mlp_predict(const float x_raw[6]) {",
            "  float x[MLP_INPUT_SIZE];",
            "  for (int i = 0; i < MLP_INPUT_SIZE; ++i) {",
            "    x[i] = (x_raw[i] - SCALER_MIN[i]) * SCALER_SCALE[i];",
            "  }",
            "",
            "  float h0[MLP_L0_SIZE];",
            "  for (int j = 0; j < MLP_L0_SIZE; ++j) {",
            "    float acc = v8c_dequant_int8(B0_Q[j], B0_INT8_SCALE);",
            "    for (int i = 0; i < MLP_INPUT_SIZE; ++i) {",
            "      acc += v8c_dequant_int8(W0_Q[i][j], W0_INT8_SCALE) * x[i];",
            "    }",
            "    h0[j] = fmaxf(0.0f, acc);",
            "  }",
            "",
            "  float h1[MLP_L1_SIZE];",
            "  for (int j = 0; j < MLP_L1_SIZE; ++j) {",
            "    float acc = v8c_dequant_int8(B1_Q[j], B1_INT8_SCALE);",
            "    for (int i = 0; i < MLP_L0_SIZE; ++i) {",
            "      acc += v8c_dequant_int8(W1_Q[i][j], W1_INT8_SCALE) * h0[i];",
            "    }",
            "    h1[j] = fmaxf(0.0f, acc);",
            "  }",
            "",
            "  float out = v8c_dequant_int8(B2_Q[0], B2_INT8_SCALE);",
            "  for (int i = 0; i < MLP_L1_SIZE; ++i) {",
            "    out += v8c_dequant_int8(W2_Q[i][0], W2_INT8_SCALE) * h1[i];",
            "  }",
            "  return fmaxf(0.0f, fminf(1.0f, out));",
            "}",
            "",
            "#endif",
            "",
        ]
    )
    return "\n".join(lines)


def render_readme() -> str:
    return """# Candidata quantizada V8C

## Origem

Este header foi gerado a partir do header float canonico `embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h`. A MLP V7C/V8B2 float continua sendo o baseline canonico.

## Tipo de compactacao

A candidata usa quantizacao deterministica simetrica INT8 por array para pesos e bias (`W0`, `B0`, `W1`, `B1`, `W2`, `B2`). Cada array possui escala propria. O scaler de entrada permanece em float e segue a politica conceitual do `sklearn.MinMaxScaler`.

## Contrato preservado

- Mesma ordem de features: `voltage_v`, `temperature_c`, `current_ma`, `delta_voltage`, `delta_temperature`, `delta_current`.
- `current_ma` e `delta_current` em mA.
- Mesma sequencia de camadas da MLP baseline.
- Sem clipping das features escaladas.
- Clipping apenas do SOC final para `[0, 1]`.
- ESP32 permanece inference-only.

## Como comparar

Executar `scripts/v8c_python_float_vs_candidate_benchmark.py` para comparar a inferencia float Python contra a candidata dequantizada simulada. Para ESP32, compilar uma variante experimental que inclua `candidate_quantized_model.h` e devolver os logs no template V8C.

## Limitacoes

Esta candidata e experimental. Na comparacao offline inicial com 140 amostras GOLDEN + EXTENDED, o `max_abs_diff` contra o baseline float ficou em aproximadamente `0.038904`, acima do limite conservador inicial de `0.01`. Portanto, ela esta implementada para benchmark e handoff experimental, mas ainda nao deve ser tratada como candidata aprovada.

Ela nao substitui o baseline V8B2, nao cria claim de campo, nao cria claim de producao, nao cria claim de sensor fisico real, nao cria claim de operacao 24/7, nao cria claim de SOH operacional e nao cria claim de diagnostico real de degradacao.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export the V8C experimental quantized candidate header.")
    parser.add_argument("--baseline-header", type=Path, default=DEFAULT_HEADER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source_text = load_header(args.baseline_header)
        header = render_header(source_text)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(header, encoding="utf-8")
    args.readme.parent.mkdir(parents=True, exist_ok=True)
    args.readme.write_text(render_readme(), encoding="utf-8")
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_header": args.output.as_posix(),
        "candidate_readme": args.readme.as_posix(),
        "scheme": "per_array_symmetric_int8",
        "status": "EXPERIMENTAL_CANDIDATE_GENERATED",
        "feature_order": FEATURE_ORDER,
    }
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
