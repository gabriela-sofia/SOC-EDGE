#!/usr/bin/env python3
"""
V8A Validation Tests
Verify that:
1. Metrics files exist
2. Decision file exists
3. Report exists
4. Schema is correct
5. canonical_v7c_model_validated=false (because V7B was tested, not V7C)
6. anomaly_layer_validated=false (because firmware doesn't report anomalies)
7. Latency is read as inference_time_ms (in milliseconds), not latency_us
8. No phrases claim canonical model was validated if it wasn't
"""

import json
import csv
from pathlib import Path
import sys

# Force UTF-8 output encoding on Windows


def test_metrics_file_exists():
    """Test: v8a_esp32_replay_metrics.json exists and is valid JSON."""
    metrics_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_esp32_replay_metrics.json"

    assert metrics_path.exists(), f"Metrics file not found: {metrics_path}"

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Verify structure
    assert "accuracy" in metrics, "Missing 'accuracy' key"
    assert "resources" in metrics, "Missing 'resources' key"
    assert metrics["esp32_replay_status"] in ["PASS", "WARN", "FAIL"], "Invalid status"

    print("[PASS] Metrics file exists and is valid JSON")
    return True


def test_decision_file_exists():
    """Test: v8a_validation_decision.json exists and contains critical fields."""
    decision_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_validation_decision.json"

    assert decision_path.exists(), f"Decision file not found: {decision_path}"

    with open(decision_path, 'r') as f:
        decision = json.load(f)

    # Verify critical fields
    assert "esp32_replay_status" in decision, "Missing esp32_replay_status"
    assert "canonical_v7c_model_validated" in decision, "Missing canonical_v7c_model_validated"
    assert "anomaly_layer_validated" in decision, "Missing anomaly_layer_validated"
    assert "legacy_v7b_model_validated" in decision, "Missing legacy_v7b_model_validated"

    print("[PASS] Decision file exists with required fields")
    return True


def test_report_exists():
    """Test: V8A_ESP32_V7B_REPLAY_VALIDATION_RESULTS.md exists."""
    report_path = Path(__file__).parent.parent / "REPORTS" / "V8A_ESP32_V7B_REPLAY_VALIDATION_RESULTS.md"

    assert report_path.exists(), f"Report not found: {report_path}"

    with open(report_path, 'r') as f:
        content = f.read()

    assert len(content) > 1000, "Report is too short (< 1000 chars)"
    assert "V8A" in content, "Report doesn't mention V8A"
    assert "PASS" in content or "pass" in content, "Report doesn't indicate pass/fail"

    print("[PASS] Report exists and has substantial content")
    return True


def test_schema_file_exists():
    """Test: v8a_serial_schema_corrected.csv exists and is properly formatted."""
    schema_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_serial_schema_corrected.csv"

    assert schema_path.exists(), f"Schema file not found: {schema_path}"

    with open(schema_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 6, f"Expected 6 fields in schema, got {len(rows)}"

    # Verify field names
    field_names = [row['field_name'] for row in rows]
    expected = ['sample_id', 'soc_final', 'inference_time_ms', 'free_heap', 'min_free_heap', 'max_alloc_heap']
    assert field_names == expected, f"Field names mismatch: {field_names} vs {expected}"

    # Verify no anomaly fields in schema
    assert 'anomaly_flag' not in field_names, "Schema incorrectly contains 'anomaly_flag'"
    assert 'anomaly_category' not in field_names, "Schema incorrectly contains 'anomaly_category'"
    assert 'latency_us' not in field_names, "Schema incorrectly contains 'latency_us' (should be inference_time_ms)"

    print("[PASS] Schema file is correct (6 fields, no anomaly fields)")
    return True


def test_canonical_not_validated():
    """Test: canonical_v7c_model_validated=false (because V7B was tested, not V7C)."""
    decision_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_validation_decision.json"

    with open(decision_path, 'r') as f:
        decision = json.load(f)

    assert decision["canonical_v7c_model_validated"] is False, \
        "canonical_v7c_model_validated should be False (V7B was tested, not canonical V7C)"

    print("[PASS] canonical_v7c_model_validated is correctly False")
    return True


def test_anomaly_not_validated():
    """Test: anomaly_layer_validated=false (firmware doesn't report anomalies)."""
    decision_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_validation_decision.json"

    with open(decision_path, 'r') as f:
        decision = json.load(f)

    assert decision["anomaly_layer_validated"] is False, \
        "anomaly_layer_validated should be False (firmware doesn't report anomalies)"

    print("[PASS] anomaly_layer_validated is correctly False")
    return True


def test_latency_in_milliseconds():
    """Test: Latency is measured in milliseconds, not microseconds."""
    metrics_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_esp32_replay_metrics.json"

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Latency should be ~0.19 ms (0.19 = 190 microseconds)
    latency_ms = metrics["resources"]["latency_mean_ms"]
    assert 0.1 < latency_ms < 1.0, f"Latency {latency_ms} ms doesn't look like milliseconds"

    # If it were microseconds, it would be ~190, which is way too high for "mean"
    # So this verifies latency is in milliseconds, not microseconds
    print(f"[PASS] Latency is in milliseconds (mean={latency_ms:.3f} ms)")
    return True


def test_no_false_canonical_claims():
    """Test: Report doesn't claim canonical model was validated if it wasn't."""
    report_path = Path(__file__).parent.parent / "REPORTS" / "V8A_ESP32_V7B_REPLAY_VALIDATION_RESULTS.md"

    with open(report_path, 'r') as f:
        content = f.read()

    # Check for false claims - look for "V7C was" or "V7C has been" in past tense
    # but allow "V7C will be" or "V7C as" or "V7C is the"
    bad_patterns = [
        "canonical v7c model has been executed",
        "canonical v7c model has been tested",
        "canonical v7c model was validated",
        "v7c model was validated on esp32",
        "this test validates the canonical v7c",
    ]

    for pattern in bad_patterns:
        assert pattern not in content.lower(), \
            f"Report contains false claim: '{pattern}'"

    # Verify correct statements about V7B vs V7C
    assert "V7B" in content, "Report should mention that V7B was tested"
    assert "V7C" in content, "Report should mention V7C as future (V8B)"

    # Verify that report clearly states V7C is NOT tested yet
    assert "NOT validated" in content or "not tested" in content or "NOT TESTED" in content, \
        "Report should explicitly state that V7C is not yet validated"

    print("[PASS] Report correctly distinguishes V7B (tested) from V7C (future)")
    return True


def test_legacy_v7b_validated():
    """Test: legacy_v7b_model_validated=true."""
    decision_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_validation_decision.json"

    with open(decision_path, 'r') as f:
        decision = json.load(f)

    assert decision["legacy_v7b_model_validated"] is True, \
        "legacy_v7b_model_validated should be True (V7B was tested and passed)"

    print("[PASS] legacy_v7b_model_validated is correctly True")
    return True


def test_tflite_validated():
    """Test: tflite_micro_pipeline_validated=true."""
    decision_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_validation_decision.json"

    with open(decision_path, 'r') as f:
        decision = json.load(f)

    assert decision["tflite_micro_pipeline_validated"] is True, \
        "tflite_micro_pipeline_validated should be True"

    print("[PASS] tflite_micro_pipeline_validated is correctly True")
    return True


def test_python_parity_validated():
    """Test: python_esp32_parity_validated=true (MAE < 0.001)."""
    decision_path = Path(__file__).parent.parent / "outputs" / "v8a_esp32_v7b_replay_validation" / "v8a_validation_decision.json"

    with open(decision_path, 'r') as f:
        decision = json.load(f)

    assert decision["python_esp32_parity_validated"] is True, \
        "python_esp32_parity_validated should be True"

    # Verify MAE is actually < 0.001
    assert decision["mae"] < 0.001, f"MAE {decision['mae']} is not < 0.001"

    print(f"[PASS] python_esp32_parity_validated is True (MAE={decision['mae']:.2e})")
    return True


def main():
    """Run all tests."""
    tests = [
        test_metrics_file_exists,
        test_decision_file_exists,
        test_report_exists,
        test_schema_file_exists,
        test_canonical_not_validated,
        test_anomaly_not_validated,
        test_latency_in_milliseconds,
        test_no_false_canonical_claims,
        test_legacy_v7b_validated,
        test_tflite_validated,
        test_python_parity_validated,
    ]

    print("\n=== V8A VALIDATION TESTS ===\n")

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
        sys.exit(1)
    else:
        print("All tests passed! [PASS]")
        sys.exit(0)


if __name__ == '__main__':
    main()
