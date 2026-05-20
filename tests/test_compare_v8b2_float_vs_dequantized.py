import subprocess
import sys
from pathlib import Path

import pytest

from scripts.compare_v8b2_float_vs_dequantized import (
    build_model,
    clip_soc,
    compare_predictions,
    compute_metrics,
    predict,
    quantize_dequantize_values,
    read_replay_csv,
    relu,
)


SIMPLE_HEADER = """
#define MLP_INPUT_SIZE 6
#define MLP_L0_SIZE 1
#define MLP_L1_SIZE 1
#define MLP_OUTPUT_SIZE 1
static const float SCALER_MIN[6] = {1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
static const float SCALER_SCALE[6] = {2.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f};
static const float W0[6][1] = {
  {0.5f},
  {0.0f},
  {0.0f},
  {0.0f},
  {0.0f},
  {0.0f}
};
static const float B0[1] = {0.1f};
static const float W1[1][1] = { {0.25f} };
static const float B1[1] = {0.0f};
static const float W2[1][1] = { {1.0f} };
static const float B2[1] = {0.0f};
"""


def test_relu_and_clip():
    assert relu(-1.0) == 0.0
    assert relu(2.0) == 2.0
    assert clip_soc(-0.2) == 0.0
    assert clip_soc(1.2) == 1.0


def test_forward_mlp_applies_scaler_and_relu():
    model = build_model(SIMPLE_HEADER)
    output = predict(model, [2.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert output == pytest.approx(0.275)


def test_quantization_dequantization_can_change_values():
    values = [0.1, 0.2, 0.3]
    dequantized = quantize_dequantize_values(values)
    assert len(dequantized) == 3
    assert dequantized != values


def test_metrics_max_mean_rmse_and_p95():
    records = [
        {"abs_diff": 0.1, "signed_diff": 0.1},
        {"abs_diff": 0.2, "signed_diff": -0.2},
        {"abs_diff": 0.3, "signed_diff": 0.3},
    ]
    metrics = compute_metrics(records)
    assert metrics["max_abs_diff"] == pytest.approx(0.3)
    assert metrics["mean_abs_diff"] == pytest.approx(0.2)
    assert metrics["rmse_diff"] == pytest.approx(((0.01 + 0.04 + 0.09) / 3) ** 0.5)
    assert metrics["p95_abs_diff"] is not None


def test_read_replay_csv_uses_explicit_columns(tmp_path):
    replay = tmp_path / "replay.csv"
    replay.write_text(
        "sample_id,mode,voltage_v,temperature_c,current_ma,delta_voltage,delta_temperature,delta_current,soc_clipped_reference\n"
        "s1,GOLDEN,2.0,0,0,0,0,0,0.275\n",
        encoding="utf-8",
    )
    rows = read_replay_csv(replay)
    assert rows[0]["sample_id"] == "s1"
    assert rows[0]["mode"] == "GOLDEN"
    assert rows[0]["features"][0] == 2.0
    assert rows[0]["soc_reference"] == 0.275


def test_compare_predictions_uses_reference_when_available(tmp_path):
    replay = tmp_path / "replay.csv"
    replay.write_text(
        "sample_id,mode,voltage_v,temperature_c,current_ma,delta_voltage,delta_temperature,delta_current,soc_clipped_reference\n"
        "s1,GOLDEN,2.0,0,0,0,0,0,0.275\n",
        encoding="utf-8",
    )
    records, summary = compare_predictions(SIMPLE_HEADER, [replay])
    assert len(records) == 1
    assert summary["global"]["n_samples"] == 1
    assert summary["reference_available"] is True
    assert records[0]["float_abs_error_vs_reference"] == pytest.approx(0.0)


def test_script_fails_when_replay_does_not_exist(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/compare_v8b2_float_vs_dequantized.py",
            "--header",
            "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h",
            "--replay-csv",
            str(tmp_path / "missing.csv"),
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "Replay CSV not found" in result.stderr


def test_real_header_reconstructs_required_arrays_if_present():
    header = Path("embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h")
    if not header.exists():
        return
    model = build_model(header.read_text(encoding="utf-8", errors="replace"))
    arrays = model["arrays"]
    assert len(arrays["SCALER_MIN"]) == 6
    assert len(arrays["W0"]) == 6
    assert len(arrays["W0"][0]) == 64
    assert len(arrays["W1"]) == 64
    assert len(arrays["W2"]) == 32
