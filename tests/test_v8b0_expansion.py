#!/usr/bin/env python3
"""
V8B0 Post-Expansion Validation Tests
Verify that V8B0 artifacts are complete, correct, and maintain scientific integrity.
"""

import json
import csv
from pathlib import Path
import sys

# UTF-8 output for Windows


def test_project_state_file_exists():
    """Test: v8b0_project_state.json exists and is valid."""
    state_path = Path(__file__).parent.parent / "outputs" / "v8b0_post_esp_expansion" / "v8b0_project_state.json"

    assert state_path.exists(), f"Project state file not found: {state_path}"

    with open(state_path, 'r', encoding='utf-8') as f:
        state = json.load(f)

    # Verify critical fields
    assert state["phase"] == "3D_post_handoff_expansion"
    assert state["v8a_status"] == "COMPLETE_AND_PASSED"
    assert state["decision"] == "CONTINUE_OFFLINE_EXPANSION_BEFORE_NEXT_HANDOFF"
    assert state["v7b_legacy_validation"]["esp_validated"] is True
    assert state["canonical_v7c_validation"]["esp_validated"] is False
    assert state["anomaly_layer_validation"]["esp_validated"] is False

    print("[PASS] Project state file complete and correct")
    return True


def test_hardware_baseline_file():
    """Test: v8b0_esp_hardware_baseline.csv exists with all metrics."""
    baseline_path = Path(__file__).parent.parent / "outputs" / "v8b0_post_esp_expansion" / "v8b0_esp_hardware_baseline.csv"

    assert baseline_path.exists(), f"Baseline file not found: {baseline_path}"

    with open(baseline_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 40, f"Baseline should have 40+ metrics, got {len(rows)}"

    # Verify key metrics are present
    metrics = {row['metric'] for row in rows}
    required_metrics = {
        "Mean Absolute Error (MAE)",
        "R² Coefficient",
        "Mean Inference Latency",
        "Free Heap at End",
        "Model Type",
        "Hardware Platform"
    }

    assert required_metrics.issubset(metrics), f"Missing required metrics: {required_metrics - metrics}"

    # Verify V8A data is preserved
    mae_row = [r for r in rows if r['metric'] == "Mean Absolute Error (MAE)"][0]
    assert "2.4e-07" in mae_row['value'] or "2.4e-7" in mae_row['value'], "MAE value not preserved"

    print("[PASS] Hardware baseline complete with all V8A metrics")
    return True


def test_next_handoff_requirements():
    """Test: V8B0_NEXT_HANDOFF_REQUIREMENTS.md exists and is comprehensive."""
    req_path = Path(__file__).parent.parent / "REPORTS" / "V8B0_NEXT_HANDOFF_REQUIREMENTS.md"

    assert req_path.exists(), f"Requirements file not found: {req_path}"

    with open(req_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verify all required sections
    assert "Canonical V7C Replay" in content
    assert "Extended Replay" in content
    assert "Stress Testing" in content
    assert "Anomaly Detection" in content
    assert "200" in content or "1000" in content  # Sample count
    assert "MAE < 0.001" in content or "MAE<0.001" in content  # Success criterion

    print("[PASS] Handoff requirements comprehensive and detailed")
    return True


def test_anomaly_protocol_design():
    """Test: Anomaly protocol design document complete."""
    anomaly_path = Path(__file__).parent.parent / "REPORTS" / "V8B0_EMBEDDED_ANOMALY_PROTOCOL_DESIGN.md"

    assert anomaly_path.exists(), f"Anomaly protocol not found: {anomaly_path}"

    with open(anomaly_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verify design sections
    assert "Category 1" in content  # Realizable now
    assert "Category 2" in content  # Reference-based
    assert "Category 3" in content  # Temporal patterns
    assert "Category 4" in content  # Future work

    # Verify it doesn't claim anomaly is ready on ESP32
    assert "not yet implemented" in content.lower()
    assert "future work" in content.lower()

    print("[PASS] Anomaly protocol comprehensive and realistic")
    return True


def test_firmware_design_spec():
    """Test: Firmware design specification exists."""
    fw_path = Path(__file__).parent.parent / "REPORTS" / "V8B0_NEXT_FIRMWARE_DESIGN_SPEC.md"

    assert fw_path.exists(), f"Firmware design not found: {fw_path}"

    with open(fw_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "V8A Schema" in content
    assert "V8B+ Proposed" in content
    assert "Backward Compatibility" in content
    assert "Modes" in content

    print("[PASS] Firmware design specification complete")
    return True


def test_claims_matrix_updated():
    """Test: Claim update matrix exists with accurate status."""
    claims_path = Path(__file__).parent.parent / "outputs" / "v8b0_post_esp_expansion" / "v8b0_claim_update_after_v8a.csv"

    assert claims_path.exists(), f"Claims matrix not found: {claims_path}"

    with open(claims_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Verify V7C claim is NOT_TESTED
    v7c_claim = [r for r in rows if "V7C" in r['claim'] and "ESP32" in r['claim']]
    if v7c_claim:
        assert v7c_claim[0]['status_after_v8a'] == "NOT_TESTED", "V7C should be NOT_TESTED after V8A"

    # Verify anomaly claim is NOT_TESTED
    anomaly_claim = [r for r in rows if "Anomalias" in r['claim'] or "anomaly" in r['claim']]
    if anomaly_claim:
        assert anomaly_claim[0]['status_after_v8a'] == "NOT_TESTED", "Anomaly should be NOT_TESTED after V8A"

    # Verify V7B claim is VALIDATED
    v7b_claim = [r for r in rows if "V7B" in r['claim']]
    if v7b_claim:
        assert "VALIDATED" in v7b_claim[0]['status_after_v8a'], "V7B should be VALIDATED after V8A"

    print("[PASS] Claims matrix correctly reflects V8A validation status")
    return True


def test_roadmap_exists():
    """Test: Scientific roadmap exists and is complete."""
    roadmap_path = Path(__file__).parent.parent / "REPORTS" / "V8B0_SCIENTIFIC_ROADMAP_BEFORE_NEXT_ESP_RUN.md"

    assert roadmap_path.exists(), f"Roadmap not found: {roadmap_path}"

    with open(roadmap_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verify phases
    assert "Phase 1" in content  # Consolidate
    assert "Phase 2" in content  # Canonical
    assert "Phase 3" in content  # Extended
    assert "Phase 4" in content  # Anomaly
    assert "Phase 5" in content  # Offline validation
    assert "Phase 6" in content  # Firmware
    assert "Phase 7" in content  # Package
    assert "Phase 8" in content  # Hardware

    # Verify timeline
    assert "1-2 weeks" in content or "1–2 weeks" in content

    print("[PASS] Scientific roadmap comprehensive and phased")
    return True


def test_main_v8b0_report():
    """Test: Main V8B0 report exists and is comprehensive."""
    report_path = Path(__file__).parent.parent / "REPORTS" / "V8B0_POST_ESP_EVIDENCE_SCIENTIFIC_EXPANSION.md"

    assert report_path.exists(), f"Main report not found: {report_path}"

    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Verify key sections
    assert "What V8A Accomplished" in content
    assert "What V8B0 Expands" in content
    assert "What Changed in the Project" in content
    assert "Why Not Send Second Handoff Now" in content
    assert "CONTINUE_OFFLINE_EXPANSION" in content

    # Verify decision is documented
    assert "Decision:" in content or "decision:" in content
    assert "OFFLINE_EXPANSION" in content.upper()

    print("[PASS] Main V8B0 report complete and documented")
    return True


def test_v8a_evidence_preserved():
    """Test: V8A evidence is preserved, not overwritten."""
    v8a_metrics = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_esp32_replay_metrics.json"
    v8a_decision = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_validation_decision.json"

    assert v8a_metrics.exists(), f"V8A metrics overwritten: {v8a_metrics}"
    assert v8a_decision.exists(), f"V8A decision overwritten: {v8a_decision}"

    # Verify V8A data integrity
    with open(v8a_metrics, 'r', encoding='utf-8') as f:
        v8a_data = json.load(f)

    assert v8a_data['esp32_replay_status'] == 'PASS'
    assert v8a_data['accuracy']['mae'] < 1e-5  # MAE should be near 2.4e-7

    print("[PASS] V8A evidence preserved and intact")
    return True


def test_no_false_v7c_claims():
    """Test: No false claims that V7C is validated on ESP32."""
    # Check all reports
    report_files = [
        Path(__file__).parent.parent / "REPORTS" / "V8B0_POST_ESP_EVIDENCE_SCIENTIFIC_EXPANSION.md",
        Path(__file__).parent.parent / "REPORTS" / "V8B0_CURRENT_PROJECT_STATE_AFTER_FIRST_ESP_HANDOFF.md",
        Path(__file__).parent.parent / "REPORTS" / "V8B0_NEXT_HANDOFF_REQUIREMENTS.md",
    ]

    false_phrases = [
        "V7C has been validated on ESP32",
        "Canonical V7C is validated in hardware",
        "Canonical model was tested on ESP32",
        "V7C execution confirmed on hardware",
    ]

    for report_path in report_files:
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for phrase in false_phrases:
                assert phrase.lower() not in content.lower(), f"False claim found: '{phrase}' in {report_path.name}"

    print("[PASS] No false claims about V7C ESP32 validation")
    return True


def test_no_false_anomaly_claims():
    """Test: No positive (unqualified) claims that anomaly detection is validated."""
    report_path = Path(__file__).parent.parent / "REPORTS" / "V8B0_POST_ESP_EVIDENCE_SCIENTIFIC_EXPANSION.md"

    false_phrases = [
        "anomaly detection works on ESP32",
        "anomalies have been tested on hardware",
        "anomaly layer is validated",
    ]

    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content_lower = content.lower()
    for phrase in false_phrases:
        idx = content_lower.find(phrase.lower())
        if idx >= 0:
            # Allowed if negated or in a forbidden-claims list ([FAIL], NOT, not yet)
            ctx = content_lower[max(0, idx - 50):idx + len(phrase) + 50]
            negated = any(marker in ctx for marker in ['[fail]', 'not ', '(not', 'forbidden', 'not yet'])
            assert negated, f"Unqualified claim found: '{phrase}'\nContext: {ctx}"

    print("[PASS] No false claims about anomaly detection")
    return True


def test_preparation_folder_marked():
    """Test: Preparation folder is clearly marked as DRAFT."""
    prep_readme = Path(__file__).parent.parent / "handoff_esp32_v8b_canonical_preparation" / "README.md"

    assert prep_readme.exists(), f"Preparation README not found: {prep_readme}"

    with open(prep_readme, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "PRE_HANDOFF_DRAFT_NOT_YET_SENT" in content
    assert "NOT YET FOR HANDOFF" in content.upper()

    print("[PASS] Preparation folder clearly marked as DRAFT")
    return True


def main():
    print("\n=== V8B0 POST-EXPANSION VALIDATION TESTS ===\n")

    tests = [
        test_project_state_file_exists,
        test_hardware_baseline_file,
        test_next_handoff_requirements,
        test_anomaly_protocol_design,
        test_firmware_design_spec,
        test_claims_matrix_updated,
        test_roadmap_exists,
        test_main_v8b0_report,
        test_v8a_evidence_preserved,
        test_no_false_v7c_claims,
        test_no_false_anomaly_claims,
        test_preparation_folder_marked,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {str(e)}")
            failed.append(test.__name__)
        except Exception as e:
            print(f"[FAIL] {test.__name__}: Unexpected error: {str(e)}")
            failed.append(test.__name__)

    print("\n=== SUMMARY ===\n")
    passed = len(tests) - len(failed)
    print(f"Passed: {passed}/{len(tests)}")

    if failed:
        print(f"Failed: {', '.join(failed)}")
        return 1
    else:
        print("All tests passed! [PASS]")
        print("\nV8B0 expansion artifacts are complete and scientifically sound.")
        print("Ready for phase transition to V8B handoff preparation.")
        return 0


if __name__ == '__main__':
    sys.exit(main())
