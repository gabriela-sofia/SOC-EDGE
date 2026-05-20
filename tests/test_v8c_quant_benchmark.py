import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts import v8c_generate_esp32_benchmark_package as package_script
from scripts import v8c_quant_benchmark_manifest as manifest_script
from scripts.v8c_python_float_vs_candidate_benchmark import compare_candidate


ROOT = Path(__file__).resolve().parents[1]
FEATURE_ORDER = [
    "voltage_v",
    "temperature_c",
    "current_ma",
    "delta_voltage",
    "delta_temperature",
    "delta_current",
]
NEW_TEXT_FILES = [
    ROOT / "docs/validacao_embarcada/protocolo_quantizacao_benchmark_esp32.md",
    ROOT / "docs/validacao_embarcada/criterios_quantizacao_benchmark_esp32.md",
    ROOT / "embedded/handoff_v8c_quant_benchmark/README.md",
]


def test_feature_order_exact():
    assert manifest_script.FEATURE_ORDER == FEATURE_ORDER
    assert package_script.FEATURE_ORDER == FEATURE_ORDER


def test_current_ma_documented_in_ma():
    manifest = manifest_script.build_manifest([])
    assert manifest["feature_units"]["current_ma"] == "mA"
    text = "\n".join(path.read_text(encoding="utf-8") for path in NEW_TEXT_FILES)
    assert "current_ma" in text
    assert "mA" in text


def test_clipping_policy_is_final_soc_only():
    manifest = manifest_script.build_manifest([])
    assert "do not clip scaled features" in manifest["scaler_policy"]
    assert manifest["clipping_policy"] == "clip only final SOC to [0, 1]"
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in NEW_TEXT_FILES)
    assert "features escaladas nao devem ser clipadas" in text
    assert "apenas o soc final" in text


def test_manifest_writers_generate_json_and_csv(tmp_path):
    output = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/v8c_quant_benchmark_manifest.py",
            "--output-dir",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    json_path = output / "v8c_quant_benchmark_manifest.json"
    csv_path = output / "v8c_quant_benchmark_file_hashes.csv"
    assert json_path.exists()
    assert csv_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["baseline_model"]["target"] == "Method B / soc_q_cycle"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows


def test_python_benchmark_runs_without_quantized_candidate(tmp_path):
    summary_path = tmp_path / "summary.json"
    csv_path = tmp_path / "predictions.csv"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/v8c_python_float_vs_candidate_benchmark.py",
            "--candidate-header",
            str(tmp_path / "candidate_missing.h"),
            "--json",
            str(summary_path),
            "--csv",
            str(csv_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["candidate_status"] == "CANDIDATE_NOT_AVAILABLE"
    assert summary["baseline_status"] == "BASELINE_REPORT_GENERATED"
    assert csv_path.exists()


def test_compare_candidate_function_reports_baseline_only(tmp_path):
    records, summary = compare_candidate(
        ROOT / "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h",
        tmp_path / "candidate_missing.h",
        [ROOT / "embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv"],
    )
    assert records
    assert summary["candidate_status"] == "CANDIDATE_NOT_AVAILABLE"
    assert summary["all_outputs_finite"] is True
    assert summary["all_soc_in_unit_interval"] is True


def test_esp32_package_manifest_and_template(tmp_path):
    manifest_path = tmp_path / "package_manifest.json"
    template_path = tmp_path / "return_template.csv"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/v8c_generate_esp32_benchmark_package.py",
            "--manifest",
            str(manifest_path),
            "--template",
            str(template_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["feature_order"] == FEATURE_ORDER
    assert "embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv" in manifest["replay_files"]
    with template_path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == package_script.LOG_FIELDS


def test_no_private_paths_in_new_files():
    forbidden = ["C:\\Users", "/Users/", ".codex", ".claude"]
    for path in NEW_TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text


def test_no_positive_forbidden_claims_in_new_docs():
    forbidden_positive = [
        "validado em campo",
        "pronto para producao",
        "sensor fisico real validado",
        "operacao 24/7 validada",
        "soh operacional",
        "diagnostico real de degradacao",
    ]
    for path in NEW_TEXT_FILES:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden_positive:
            index = text.find(phrase)
            if index == -1:
                continue
            context = text[max(0, index - 80) : index + len(phrase) + 80]
            assert any(marker in context for marker in ["nao", "sem", "proib", "limite"]), context


def test_new_docs_are_portuguese_technical_text():
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in NEW_TEXT_FILES)
    required_terms = ["objetivo", "criterios", "validacao", "candidata", "baseline", "inferência", "quantizacao"]
    ascii_fallback_terms = ["inferencia"]
    assert "objetivo" in text
    assert "candidata" in text
    assert "quantizacao" in text
    assert ("inferência" in text) or any(term in text for term in ascii_fallback_terms)


def test_no_heavy_versionable_artifacts_in_v8c_layer():
    allowed_suffixes = {".md", ".csv", ".json"}
    for path in (ROOT / "embedded/handoff_v8c_quant_benchmark").rglob("*"):
        if path.is_file():
            assert path.suffix in allowed_suffixes
            assert path.stat().st_size < 200_000

