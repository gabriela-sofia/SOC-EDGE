import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts import v8c_generate_esp32_benchmark_package as package_script
from scripts import v8c_optimize_quantized_candidate as optimize_script
from scripts import v8c_quant_benchmark_manifest as manifest_script
from scripts.v8c_python_float_vs_candidate_benchmark import compare_candidate, compare_variants


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
    ROOT / "embedded/handoff_v8c_quant_benchmark/include/README_candidate_quantized.md",
]
DEFAULT_CANDIDATE = ROOT / "embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model.h"
DEFAULT_OPTIMIZED_CANDIDATE = (
    ROOT / "embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model_optimized.h"
)


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
    assert data["experimental_candidate"]["candidate_header"] == (
        "embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model.h"
    )
    assert data["experimental_candidate"]["optimized_candidate_header"] == (
        "embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model_optimized.h"
    )
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


def test_candidate_header_exists_and_is_detected():
    assert DEFAULT_CANDIDATE.exists()
    records, summary = compare_candidate(
        ROOT / "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h",
        DEFAULT_CANDIDATE,
        [ROOT / "embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv"],
    )
    assert records
    assert summary["candidate_status"] == "CANDIDATE_AVAILABLE"
    assert summary["candidate_scheme"] == "per_array_symmetric_int8_dequantized_forward"
    assert summary["candidate_diff_vs_float"]["n"] == 20
    assert summary["candidate_nan_inf_count"] == 0
    assert summary["candidate_soc_summary"]["min"] >= 0.0
    assert summary["candidate_soc_summary"]["max"] <= 1.0
    assert summary["conservative_max_abs_diff_limit"] == 0.01
    assert summary["candidate_within_conservative_limit"] is False
    assert summary["all_outputs_finite"] is True
    assert summary["all_soc_in_unit_interval"] is True


def test_candidate_header_preserves_contract_text():
    text = DEFAULT_CANDIDATE.read_text(encoding="utf-8")
    assert "voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current" in text
    assert "current_ma mA" in text
    assert "do not clip scaled features" in text
    assert "clip only final SOC" in text
    assert "candidate_mlp_predict" in text
    assert "int8_t W0_Q" in text


def test_optimized_candidate_header_exists_and_preserves_contract_text():
    assert DEFAULT_OPTIMIZED_CANDIDATE.exists()
    text = DEFAULT_OPTIMIZED_CANDIDATE.read_text(encoding="utf-8")
    assert "experimental" in text.lower()
    assert "Baseline remains MLP V7C/V8B2 float" in text
    assert "voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current" in text
    assert "current_ma mA" in text
    assert "do not clip scaled features" in text
    assert "clip only final SOC" in text
    assert "candidate_optimized_mlp_predict" in text
    assert "int16_t W0_Q" in text
    assert "C:\\Users" not in text
    assert "/Users/" not in text


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
    assert manifest["candidate_header"] == "embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model.h"
    assert manifest["optimized_candidate_header"] == (
        "embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model_optimized.h"
    )
    assert manifest["baseline_header"] == "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h"
    variants = {item["model_variant"] for item in manifest["candidate_variants"]}
    assert {"v8c_int8_per_array_candidate", "v8c_optimized_candidate"} <= variants
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
    for path in [DEFAULT_CANDIDATE, DEFAULT_OPTIMIZED_CANDIDATE]:
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
            assert any(marker in context for marker in ["nao", "nenhuma", "sem", "proib", "limite"]), context


def test_new_docs_are_portuguese_technical_text():
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in NEW_TEXT_FILES)
    required_terms = ["objetivo", "criterios", "validacao", "candidata", "baseline", "inferência", "quantizacao"]
    ascii_fallback_terms = ["inferencia"]
    assert "objetivo" in text
    assert "candidata" in text
    assert "quantizacao" in text
    assert ("inferência" in text) or any(term in text for term in ascii_fallback_terms)


def test_no_heavy_versionable_artifacts_in_v8c_layer():
    allowed_suffixes = {".md", ".csv", ".json", ".h"}
    for path in (ROOT / "embedded/handoff_v8c_quant_benchmark").rglob("*"):
        if path.is_file():
            assert path.suffix in allowed_suffixes
            assert path.stat().st_size < 200_000


def test_default_candidate_script_reports_available(tmp_path):
    summary_path = tmp_path / "summary.json"
    csv_path = tmp_path / "predictions.csv"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/v8c_python_float_vs_candidate_benchmark.py",
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
    assert summary["candidate_status"] == "CANDIDATE_AVAILABLE"
    assert summary["best_variant_id"] == "v8c_optimized_candidate"
    assert summary["best_variant_within_conservative_limit"] is True
    assert len(summary["variant_ranking"]) >= 2
    assert summary["candidate_nan_inf_count"] == 0
    assert summary["candidate_soc_summary"]["min"] >= 0.0
    assert summary["candidate_soc_summary"]["max"] <= 1.0
    with csv_path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert "model_variant" in header


def test_compare_variants_reports_ranking_and_optimized_candidate():
    records, summary = compare_variants(
        ROOT / "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h",
        DEFAULT_CANDIDATE,
        DEFAULT_OPTIMIZED_CANDIDATE,
        [ROOT / "embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv"],
    )
    variants = {record["model_variant"] for record in records}
    assert {"baseline_float", "v8c_int8_per_array_candidate", "v8c_optimized_candidate"} <= variants
    assert summary["variant_ranking"]
    assert summary["best_variant_id"] == "v8c_optimized_candidate"
    assert summary["best_variant_within_conservative_limit"] is True
    assert summary["all_outputs_finite"] is True
    assert summary["all_soc_in_unit_interval"] is True


def test_compare_variants_fallback_when_optimized_missing(tmp_path):
    records, summary = compare_variants(
        ROOT / "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h",
        DEFAULT_CANDIDATE,
        tmp_path / "candidate_quantized_model_optimized_missing.h",
        [ROOT / "embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv"],
    )
    variants = {record["model_variant"] for record in records}
    assert "v8c_int8_per_array_candidate" in variants
    assert "v8c_optimized_candidate" not in variants
    assert summary["candidate_status"] == "CANDIDATE_AVAILABLE"


def test_optimizer_generates_variant_ranking(tmp_path):
    ranking_csv = tmp_path / "ranking.csv"
    ranking_json = tmp_path / "ranking.json"
    header = tmp_path / "candidate_quantized_model_optimized.h"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/v8c_optimize_quantized_candidate.py",
            "--ranking-csv",
            str(ranking_csv),
            "--ranking-json",
            str(ranking_json),
            "--optimized-header",
            str(header),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(ranking_json.read_text(encoding="utf-8"))
    assert summary["best_variant_id"] == "v8c_int16_per_output_bias_float"
    assert summary["best_variant_within_conservative_limit"] is True
    assert header.exists()
    assert optimize_script.CONSERVATIVE_MAX_ABS_DIFF_LIMIT == 0.01


def test_reports_v8c_quant_benchmark_is_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", "-q", "reports/v8c_quant_benchmark/example.json"],
        cwd=ROOT,
    )
    assert result.returncode == 0
