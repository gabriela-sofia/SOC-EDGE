import json
import subprocess
import sys
from pathlib import Path

from scripts.export_v8b2_quantized_header import render_header


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


def test_export_header_contains_guard_int8_and_candidate_notice():
    rendered = render_header(HEADER, "per_array_symmetric_int8")
    assert "#ifndef CANONICAL_MODEL_WEIGHTS_V8B2_INT8_CANDIDATE_H" in rendered
    assert "#include <stdint.h>" in rendered
    assert "int8_t W0_Q" in rendered
    assert "Header candidato para experimento de quantizacao" in rendered
    assert "Nao representa firmware INT8 validado" in rendered
    assert "1.0f" in rendered


def test_export_script_writes_header_and_manifest(tmp_path):
    source = tmp_path / "weights.h"
    output = tmp_path / "candidate.h"
    manifest = tmp_path / "manifest.json"
    source.write_text(HEADER, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_v8b2_quantized_header.py",
            "--header",
            str(source),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert output.exists()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["status"] == "offline quantization candidate"
    assert payload["scheme"] == "per_array_symmetric_int8"


def test_export_script_fails_when_header_missing(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_v8b2_quantized_header.py",
            "--header",
            str(tmp_path / "missing.h"),
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "Header not found" in result.stderr
