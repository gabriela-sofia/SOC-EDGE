import pytest

from scripts.compare_v8b2_quantization_schemes import (
    compare_schemes,
    evaluate_scheme,
    make_dequantized_arrays,
    scale_for_values,
)


HEADER = """
#define MLP_INPUT_SIZE 6
#define MLP_L0_SIZE 1
#define MLP_L1_SIZE 1
#define MLP_OUTPUT_SIZE 1
static const float SCALER_MIN[6] = {0,0,0,0,0,0};
static const float SCALER_SCALE[6] = {1,1,1,1,1,1};
static const float W0[6][1] = {{0.5f},{0},{0},{0},{0},{0}};
static const float B0[1] = {0.1f};
static const float W1[1][1] = {{0.25f}};
static const float B1[1] = {0.0f};
static const float W2[1][1] = {{1.0f}};
static const float B2[1] = {0.0f};
"""


def replay_row():
    return {
        "features": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "soc_reference": 0.15,
    }


def test_global_symmetric_int8_uses_one_scale():
    _, scales, warnings = make_dequantized_arrays(HEADER, "global_symmetric_int8")
    assert list(scales) == ["GLOBAL"]
    assert warnings == []


def test_per_array_symmetric_int8_uses_scale_per_model_array():
    _, scales, warnings = make_dequantized_arrays(HEADER, "per_array_symmetric_int8")
    assert set(scales) == {"W0", "B0", "W1", "B1", "W2", "B2"}
    assert warnings == []


def test_quantization_preserves_array_shapes():
    arrays, _, _ = make_dequantized_arrays(HEADER, "per_array_symmetric_int8")
    assert len(arrays["W0"]) == 6
    assert len(arrays["W0"][0]) == 1
    assert len(arrays["B0"]) == 1


def test_evaluate_scheme_reports_metrics_and_compression():
    result = evaluate_scheme(HEADER, [replay_row()], "per_array_symmetric_int8")
    assert result["n_samples"] == 1
    assert result["compression_ratio"] == 4.0
    assert result["n_scales"] == 6
    assert result["rmse_diff_float_vs_dequant"] is not None


def test_ranking_chooses_lowest_rmse(tmp_path):
    replay = tmp_path / "replay.csv"
    replay.write_text(
        "sample_id,mode,voltage_v,temperature_c,current_ma,delta_voltage,delta_temperature,delta_current,soc_clipped_reference\n"
        "s1,GOLDEN,1.0,0,0,0,0,0,0.15\n",
        encoding="utf-8",
    )
    payload = compare_schemes(HEADER, [replay])
    rmses = {row["scheme"]: row["rmse_diff_float_vs_dequant"] for row in payload["schemes"]}
    assert payload["ranking"][0] == min(rmses, key=rmses.get)


def test_scale_for_zero_values_is_one():
    assert scale_for_values([0.0, -0.0]) == pytest.approx(1.0)
