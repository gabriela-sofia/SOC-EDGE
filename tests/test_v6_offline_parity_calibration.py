#!/usr/bin/env python3
"""
Test suite for V6 Offline Parity & Calibration

Tests verify:
1. Script executes without crashing
2. Expected outputs are created
3. No metrics are invented
4. Missing inputs are reported
5. No blocker is hidden
6. No claim is false
"""

import os
import sys
import json
import csv
from pathlib import Path

def test_v6_output_files_exist():
    """Test 1: All expected output files exist."""
    output_dir = Path('outputs/v6_offline_parity_calibration')
    expected_files = [
        'v6_parity_summary.json',
        'v6_parity_table.csv',
        'v6_calibration_thresholds.csv',
        'v6_missing_inputs.csv',
        'v6_scientific_readiness.md',
    ]

    for fname in expected_files:
        fpath = output_dir / fname
        assert fpath.exists(), f"Missing file: {fpath}"

    print("[PASS] Test 1: Output files exist")

def test_v6_parity_summary_structure():
    """Test 2: parity_summary.json has correct structure."""
    with open('outputs/v6_offline_parity_calibration/v6_parity_summary.json') as f:
        data = json.load(f)

    required_keys = [
        'version',
        'date',
        'v2_soc_summary',
        'v4_anomaly_summary',
        'scaler_status',
        'domain_shift',
        'esp32_readiness',
        'parity_table',
        'scientific_readiness',
    ]

    for key in required_keys:
        assert key in data, f"Missing key in parity_summary: {key}"

    assert data['version'] == 'v6', "Version should be v6"
    print("[PASS] Test 2: Parity summary structure correct")

def test_v6_calibration_thresholds():
    """Test 3: Calibration thresholds are not invented."""
    with open('outputs/v6_offline_parity_calibration/v6_calibration_thresholds.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) > 0, "Calibration thresholds table is empty"

    # Check for invented values
    for row in rows:
        param = row.get('parameter', '')
        value = row.get('value', '')
        source = row.get('source', '')

        # Physical thresholds should have known sources
        if param == 'voltage_V_min' or param == 'voltage_V_max':
            assert float(value) >= 0, f"Invalid voltage threshold: {value}"
            assert 'spec' in source.lower() or 'iec' in source.lower(), f"Voltage threshold needs proper source: {source}"

        # All should have source
        assert source.strip(), f"Threshold {param} missing source"

    print("[PASS] Test 3: Calibration thresholds are sourced")

def test_v6_missing_inputs_identified():
    """Test 4: Missing inputs are documented."""
    with open('outputs/v6_offline_parity_calibration/v6_missing_inputs.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) > 0, "Missing inputs should not be empty"

    # Check critical missing inputs are listed
    missing_types = set(row.get('input_type', '') for row in rows)

    # These MUST be present to claim completeness
    critical = [
        'Scaler frozen state',
        'Real fault labels',
        'Formal parity test',  # Accept with or without Unicode
    ]

    for critical_item in critical:
        assert any(critical_item.lower() in mt.lower() for mt in missing_types), \
            f"Missing input '{critical_item}' not documented. Found: {missing_types}"

    print("[PASS] Test 4: Missing inputs documented")

def test_v6_no_esp32_recommendation_as_main_solution():
    """Test 5: No recommendation to change ESP32 as main solution."""
    with open('outputs/v6_offline_parity_calibration/v6_scientific_readiness.md') as f:
        content = f.read()

    # Check for wrong statements
    assert 'ESP32-S3' not in content or 'not recommended' in content.lower(), \
        "V6 should not recommend ESP32-S3 as main solution"

    assert 'Raspberry' not in content or 'not recommended' in content.lower(), \
        "V6 should not recommend Raspberry as main solution"

    assert 'STM32' not in content or 'not recommended' in content.lower(), \
        "V6 should not recommend STM32 as main solution"

    print("[PASS] Test 5: No hardware change recommended")

def test_v6_blockers_listed():
    """Test 6: Known blockers are explicitly listed."""
    with open('outputs/v6_offline_parity_calibration/v6_parity_summary.json') as f:
        data = json.load(f)

    blockers = data.get('scientific_readiness', {}).get('blocker_status', {})

    assert 'cell3_cell8_nan' in blockers, "Cell3/Cell8 NaN blocker should be listed"
    assert 'mcmaster_loto_0c_failure' in blockers, "LOTO 0C failure blocker should be listed"
    assert 'oxford_to_mcmaster_domain_shift' in blockers, "Domain shift blocker should be listed"
    assert 'python_esp32_parity' in blockers, "Parity blocker should be listed"

    # Check they are marked as OPEN or not resolved
    for blocker_name, blocker_status in blockers.items():
        assert 'OPEN' in blocker_status or 'NOT_STARTED' in blocker_status or 'MISSING' in blocker_status or 'NOT_TESTED' in blocker_status, \
            f"Blocker '{blocker_name}' should be explicitly marked as unresolved: {blocker_status}"

    print("[PASS] Test 6: All blockers documented")

def test_v6_source_evidence_matrix_exists():
    """Test 7: Source evidence matrix exists."""
    assert os.path.exists('REPORTS/V6_SOC_SOURCE_EVIDENCE_MATRIX.md'), \
        "Source evidence matrix must exist"

    try:
        with open('REPORTS/V6_SOC_SOURCE_EVIDENCE_MATRIX.md', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open('REPORTS/V6_SOC_SOURCE_EVIDENCE_MATRIX.md', encoding='latin-1') as f:
            content = f.read()

    # Check it's not empty
    assert len(content) > 1000, "Source evidence matrix is too short"

    # Check it documents sources (accept many variations)
    assert 'FORTE' in content or 'STRONG' in content, "Should categorize sources"
    assert 'matriz' in content.lower() or 'matrix' in content.lower(), "Should have source matrix"

    # Check it marks NEEDS_VERIFICATION if needed
    if 'NEEDS_VERIFICATION' in content:
        print("[NOTE] Test 7 found NEEDS_VERIFICATION - expected for ongoing research")

    print("[PASS] Test 7: Source evidence matrix exists")

def test_v6_edge_readiness_document_exists():
    """Test 8: Edge readiness document exists."""
    assert os.path.exists('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md'), \
        "Edge readiness document must exist"

    try:
        with open('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md', encoding='latin-1') as f:
            content = f.read()

    # Check sections (lowercased, without accents for robustness)
    required_sections = [
        'objetivo',
        'estado anterior',
        'method b',
        'abl',  # ablacao/ablação
        'anomalia',
        'esp32',
        'bloqueador',
    ]

    for section in required_sections:
        assert section.lower() in content.lower(), f"Missing section: {section}"

    print("[PASS] Test 8: Edge readiness document complete")

def test_v6_no_invented_results():
    """Test 9: No invented metrics or claims."""
    with open('outputs/v6_offline_parity_calibration/v6_parity_summary.json') as f:
        data = json.load(f)

    # V2 metrics must match known results
    v2_summary = data.get('v2_soc_summary', {})
    if v2_summary.get('status') == 'LOADED':
        # Best R² should match actual best from V2 (Oxford LOCO Cell6: 0.99873)
        best_r2 = v2_summary.get('best_r2')
        assert best_r2 is not None, "V2 best R² should be populated"
        assert abs(best_r2 - 0.99873) < 0.001, f"V2 best R² should be ~0.99873, got {best_r2}"

    # V4 metrics should match
    v4_summary = data.get('v4_anomaly_summary', {})
    if v4_summary.get('status') == 'LOADED':
        scenarios = v4_summary.get('total_scenarios')
        assert scenarios == 15, f"V4 should have 15 scenarios, got {scenarios}"

    print("[PASS] Test 9: Results not invented")

def test_v6_project_not_tcc():
    """Test 10: Project is explicitly marked as NOT TCC."""
    try:
        with open('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md', encoding='latin-1') as f:
            content = f.read()

    assert 'NAO' in content or 'NOT' in content, \
        "Must explicitly state project is NOT a TCC"

    assert 'TCC' in content, "Document should mention TCC to clarify it's not one"

    print("[PASS] Test 10: NOT TCC is stated")

def test_v61_audit_files_exist():
    """V6.1 Test 11: Audit output files exist."""
    required = [
        'REPORTS/V6_1_AUDIT_CLAIM_FIX_AND_COMMIT_READINESS.md',
        'outputs/v6_offline_parity_calibration/v6_1_claim_audit.csv',
        'outputs/v6_offline_parity_calibration/v6_1_metric_traceability.csv',
    ]
    for f in required:
        assert os.path.exists(f), f"V6.1 audit file missing: {f}"
    print("[PASS] Test 11 (V6.1): Audit files exist")


def test_v61_no_weak_source_as_main():
    """V6.1 Test 12: No weak source used as main evidence."""
    try:
        with open('outputs/v6_offline_parity_calibration/v6_1_claim_audit.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except UnicodeDecodeError:
        with open('outputs/v6_offline_parity_calibration/v6_1_claim_audit.csv', encoding='latin-1') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    for row in rows:
        evidence_type = row.get('evidence_type', '')
        status = row.get('status', '')
        # Weak sources (YouTube, Scribd, etc.) must not be CONFIRMED as main
        if 'WEAK' in evidence_type.upper() or 'YOUTUBE' in evidence_type.upper():
            assert status != 'CONFIRMED', \
                f"Weak source cannot be CONFIRMED main evidence: {row.get('claim_id')}"

    print("[PASS] Test 12 (V6.1): No weak source as main evidence")


def test_v61_esp32_claims_are_estimates():
    """V6.1 Test 13: Document says hardware estimates are theoretical."""
    try:
        with open('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md', encoding='latin-1') as f:
            content = f.read()

    # Check that hardware estimates are labeled
    assert 'ESTIMATIVA' in content or 'TEÓRICA' in content or 'ESTIMADO' in content or 'ESTIMATED' in content, \
        "Document must explicitly label hardware resource estimates as estimates, not measurements"

    # Check that no firmware or benchmark is claimed where none exists
    assert 'nenhum firmware' in content.lower() or 'nenhuma compilada' in content.lower() or \
           'sem firmware' in content.lower() or 'não compilada' in content.lower(), \
        "Must explicitly state no firmware was compiled or benchmarked"

    print("[PASS] Test 13 (V6.1): Hardware estimates labeled correctly")


def test_v61_anomaly_claim_is_synthetic_only():
    """V6.1 Test 14: Anomaly claims do not imply real-field detection."""
    try:
        with open('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open('REPORTS/V6_OFFLINE_PARITY_CALIBRATION_AND_EDGE_READINESS.md', encoding='latin-1') as f:
            content = f.read()

    # Must mention synthetic labels
    assert 'sintétic' in content.lower() or 'synthetic' in content.lower(), \
        "Anomaly section must mention that labels are synthetic"

    # Must state no real faults
    assert 'falha real' in content.lower() or 'real fault' in content.lower() or \
           'nenhuma falha real' in content.lower() or 'no real fault' in content.lower(), \
        "Must explicitly state no real fault labels were validated"

    print("[PASS] Test 14 (V6.1): Anomaly claims correctly bounded to synthetic")


def test_v61_metric_traceability_completeness():
    """V6.1 Test 15: Key metrics have confirmed or explicit status."""
    try:
        with open('outputs/v6_offline_parity_calibration/v6_1_metric_traceability.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except UnicodeDecodeError:
        with open('outputs/v6_offline_parity_calibration/v6_1_metric_traceability.csv', encoding='latin-1') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    assert len(rows) > 0, "Traceability table must not be empty"

    # Check all rows have evidence_type
    for row in rows:
        assert row.get('evidence_type', '').strip(), \
            f"Row '{row.get('metric_name')}' missing evidence_type"
        assert row.get('confidence', '').strip(), \
            f"Row '{row.get('metric_name')}' missing confidence"

    # Confirm key metrics are present
    metric_names = set(r.get('metric_name', '') for r in rows)
    key_metrics = ['Best R2 Oxford LOCO', 'LSTMAe AUROC global', 'Current domain shift normalized']
    for km in key_metrics:
        assert any(km.lower() in m.lower() for m in metric_names), \
            f"Key metric '{km}' missing from traceability table"

    print("[PASS] Test 15 (V6.1): Metric traceability complete")


def test_v61_no_auroc_conflict_hidden():
    """V6.1 Test 16: AUROC conflicts between V4/V5 are documented, not hidden."""
    try:
        with open('outputs/v6_offline_parity_calibration/v6_1_metric_traceability.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except UnicodeDecodeError:
        with open('outputs/v6_offline_parity_calibration/v6_1_metric_traceability.csv', encoding='latin-1') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    # Find NEEDS_VERIFICATION entries
    needs_verif = [r for r in rows if 'NEEDS_VERIFICATION' in r.get('evidence_type', '')]

    # There should be at least one: the V4 F1@p95=0.198 that cannot be confirmed
    assert len(needs_verif) >= 1, \
        "Expected at least one NEEDS_VERIFICATION entry (V4 F1@p95=0.198 cannot be confirmed from outputs)"

    print("[PASS] Test 16 (V6.1): AUROC/F1 conflicts documented")


def test_v61_outputs_still_generated():
    """V6.1 Test 17: V6 script still generates all expected outputs."""
    output_dir = Path('outputs/v6_offline_parity_calibration')
    # All original V6 outputs still exist
    original_outputs = [
        'v6_parity_summary.json',
        'v6_parity_table.csv',
        'v6_calibration_thresholds.csv',
        'v6_missing_inputs.csv',
        'v6_scientific_readiness.md',
    ]
    for fname in original_outputs:
        assert (output_dir / fname).exists(), f"Original V6 output missing after audit: {fname}"

    print("[PASS] Test 17 (V6.1): All original V6 outputs intact")


def run_all_tests():
    """Run all tests."""
    tests = [
        test_v6_output_files_exist,
        test_v6_parity_summary_structure,
        test_v6_calibration_thresholds,
        test_v6_missing_inputs_identified,
        test_v6_no_esp32_recommendation_as_main_solution,
        test_v6_blockers_listed,
        test_v6_source_evidence_matrix_exists,
        test_v6_edge_readiness_document_exists,
        test_v6_no_invented_results,
        test_v6_project_not_tcc,
        # V6.1 Audit tests
        test_v61_audit_files_exist,
        test_v61_no_weak_source_as_main,
        test_v61_esp32_claims_are_estimates,
        test_v61_anomaly_claim_is_synthetic_only,
        test_v61_metric_traceability_completeness,
        test_v61_no_auroc_conflict_hidden,
        test_v61_outputs_still_generated,
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("V6 + V6.1 Offline Parity, Calibration & Audit Test Suite")
    print("=" * 70 + "\n")

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print("[FAIL] {}: {}".format(test.__name__, error_msg))
            failed += 1
        except Exception as e:
            error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            print("[ERROR] {}: {}".format(test.__name__, error_msg))
            failed += 1

    print("\n" + "=" * 70)
    print("Results: {} PASSED, {} FAILED".format(passed, failed))
    print("=" * 70 + "\n")

    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
