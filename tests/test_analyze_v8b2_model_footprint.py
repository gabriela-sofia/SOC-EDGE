import subprocess
import sys
from pathlib import Path

from scripts.analyze_v8b2_model_footprint import (
    analyze_footprint,
    parse_defines,
    parse_float_arrays,
)


SYNTHETIC_HEADER = """
#define MLP_INPUT_SIZE 2
#define MLP_L0_SIZE 3
#define MLP_L1_SIZE 2
#define MLP_OUTPUT_SIZE 1
static const float W0[2][3] = {
  {1.0f, -2.0f, 3.0f},
  {4.0f, 5.0f, -6.0f}
};
static const float B0[3] = {0.1f, 0.2f, 0.3f};
"""


def test_parse_defines_extracts_mlp_dimensions():
    defines = parse_defines(SYNTHETIC_HEADER)
    assert defines["MLP_INPUT_SIZE"] == 2
    assert defines["MLP_L0_SIZE"] == 3
    assert defines["MLP_L1_SIZE"] == 2
    assert defines["MLP_OUTPUT_SIZE"] == 1


def test_parse_float_arrays_extracts_names_dimensions_and_values():
    arrays = parse_float_arrays(SYNTHETIC_HEADER)
    assert [array.name for array in arrays] == ["W0", "B0"]
    assert arrays[0].dimensions == [2, 3]
    assert arrays[0].values == [1.0, -2.0, 3.0, 4.0, 5.0, -6.0]
    assert arrays[1].dimensions == [3]
    assert arrays[1].parameter_count == 3


def test_analyze_footprint_counts_parameters_and_bytes():
    report = analyze_footprint(SYNTHETIC_HEADER)
    assert report["number_of_arrays_parsed"] == 2
    assert report["total_float_parameters"] == 9
    assert report["estimated_float32_bytes"] == 36
    assert report["estimated_int8_bytes"] == 9
    assert report["theoretical_compression_ratio"] == 4.0
    assert report["warnings"] == []


def test_missing_header_returns_clear_error(tmp_path):
    missing = tmp_path / "missing.h"
    result = subprocess.run(
        [sys.executable, "scripts/analyze_v8b2_model_footprint.py", "--header", str(missing)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "Header not found" in result.stderr


def test_real_header_integration_if_present():
    header = Path("embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h")
    if not header.exists():
        return
    report = analyze_footprint(header.read_text(encoding="utf-8", errors="replace"))
    assert report["defines"]["MLP_INPUT_SIZE"] == 6
    assert report["total_float_parameters"] > 0
