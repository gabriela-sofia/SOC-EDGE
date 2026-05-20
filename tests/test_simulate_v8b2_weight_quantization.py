import subprocess
import sys
from pathlib import Path

import pytest

from scripts.simulate_v8b2_weight_quantization import (
    quantize_symmetric_int8,
    simulate_quantization,
)


def test_symmetric_quantization_calculates_scale_and_error():
    metrics = quantize_symmetric_int8([-1.0, 0.0, 1.0])
    assert metrics["n"] == 3
    assert metrics["max_abs"] == 1.0
    assert metrics["scale"] == pytest.approx(1.0 / 127.0)
    assert metrics["max_abs_error"] == pytest.approx(0.0)
    assert metrics["rmse"] == pytest.approx(0.0)


def test_zero_array_does_not_break_quantization():
    metrics = quantize_symmetric_int8([0.0, -0.0, 0.0])
    assert metrics["scale"] == 1.0
    assert metrics["max_abs_error"] == 0.0
    assert metrics["mean_abs_error"] == 0.0
    assert metrics["rmse"] == 0.0


def test_dequantization_error_is_reported_for_non_exact_values():
    metrics = quantize_symmetric_int8([0.0, 0.1, 0.2, 0.3])
    assert metrics["max_abs_error"] is not None
    assert metrics["mean_abs_error"] is not None
    assert metrics["rmse"] is not None
    assert metrics["max_abs_error"] >= 0.0


def test_simulation_parses_arrays_and_returns_scope():
    header = "static const float W0[2] = {1.0f, -1.0f};"
    report = simulate_quantization(header)
    assert report["array_count"] == 1
    assert report["total_values"] == 2
    assert "nao e validacao INT8 embarcada" in report["scope"]
    assert report["arrays"]["W0"]["n"] == 2


def test_missing_header_returns_clear_error(tmp_path):
    missing = tmp_path / "missing.h"
    result = subprocess.run(
        [sys.executable, "scripts/simulate_v8b2_weight_quantization.py", "--header", str(missing)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "Header not found" in result.stderr


def test_real_header_integration_if_present(tmp_path):
    header = Path("embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h")
    if not header.exists():
        return
    result = subprocess.run(
        [
            sys.executable,
            "scripts/simulate_v8b2_weight_quantization.py",
            "--header",
            str(header),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "not" not in result.stderr.lower()
    assert (tmp_path / "v8b2_weight_quantization_report.json").exists()
