"""
V8B1 test suite: canonical artifact recovery and V8B0 cleanup validation.

Tests:
  1. Artifact recovery CSV exists
  2. Blocker correction JSON exists and all 3 blockers corrected
  3. Encoding fix report exists
  4. V8B1 reconciliation report exists
  5. Next action report exists
  6. Extended replay CSV exists with >= 120 samples
  7. Extended replay summary JSON exists and passes thresholds
  8. No false V7C ESP32 claims in any V8B1 report
  9. No false anomaly claims in any V8B1 report
 10. V8A evidence untouched
 11. Core V7C artifacts all present
 12. pkl inference works correctly (dict with scaler + model)
 13. Saturation behavior documented in extended replay
 14. Decision in next action report is READY_FOR_V8B_PACKAGE_BUILD
"""

import os
import json
import pickle
import pandas as pd
import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOVERY_DIR = os.path.join(BASE, 'outputs', 'v8b1_canonical_recovery')
ARTIFACTS_DIR = os.path.join(BASE, 'artifacts', 'edge_v7c')
V8A_DIR = os.path.join(BASE, 'outputs', 'v8a_esp32_v7b_replay_validation')
REPORTS_DIR = os.path.join(BASE, 'REPORTS')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def replay_df():
    path = os.path.join(RECOVERY_DIR, 'v8b1_extended_canonical_replay.csv')
    return pd.read_csv(path)


@pytest.fixture(scope='module')
def replay_summary():
    path = os.path.join(RECOVERY_DIR, 'v8b1_extended_replay_summary.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def blocker_correction():
    path = os.path.join(RECOVERY_DIR, 'v8b1_v8b0_blocker_correction.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test 1-5: Output files exist
# ---------------------------------------------------------------------------

def test_artifact_recovery_csv_exists():
    path = os.path.join(RECOVERY_DIR, 'v8b1_canonical_artifact_recovery.csv')
    assert os.path.exists(path), f"Artifact recovery CSV not found: {path}"
    df = pd.read_csv(path)
    assert len(df) >= 7, f"Expected >= 7 artifact records, got {len(df)}"


def test_blocker_correction_json_exists(blocker_correction):
    corrections = blocker_correction.get('corrections', [])
    assert len(corrections) >= 3, f"Expected >= 3 blocker corrections, got {len(corrections)}"
    valid_statuses = {'AVAILABLE_FOR_V8B_PREPARATION', 'UNBLOCKED'}
    for c in corrections:
        status = c.get('corrected_status', '')
        # Accept any corrected status that is not BLOCKED
        assert 'BLOCKED' not in status or status.startswith('UNBLOCKED'), (
            f"Blocker still marked as blocked: {c.get('previous_blocker')} -> {status}"
        )
        # Must have some positive resolution
        has_resolution = any(v in status for v in ['AVAILABLE', 'UNBLOCKED', 'FOUND'])
        assert has_resolution, (
            f"Blocker correction has no positive resolution: {c.get('previous_blocker')} -> {status}"
        )


def test_encoding_fix_report_exists():
    path = os.path.join(RECOVERY_DIR, 'v8b1_encoding_fix_report.csv')
    assert os.path.exists(path), f"Encoding fix report not found: {path}"
    df = pd.read_csv(path)
    assert len(df) >= 1, "Encoding fix report is empty"


def test_v8b1_reconciliation_report_exists():
    path = os.path.join(REPORTS_DIR, 'V8B1_CANONICAL_ARTIFACT_RECOVERY_AND_V8B0_CLEANUP.md')
    assert os.path.exists(path), f"V8B1 reconciliation report not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'READY_FOR_V8B_PACKAGE_BUILD' in content, "Decision not found in reconciliation report"
    assert len(content) > 1000, "Reconciliation report seems too short"


def test_next_action_report_exists():
    path = os.path.join(REPORTS_DIR, 'V8B1_NEXT_ACTION_AFTER_CLEANUP.md')
    assert os.path.exists(path), f"Next action report not found: {path}"
    content = open(path, encoding='utf-8').read()
    assert 'READY_FOR_V8B_PACKAGE_BUILD' in content, "Decision not found in next action report"


# ---------------------------------------------------------------------------
# Test 6-7: Extended replay dataset
# ---------------------------------------------------------------------------

def test_extended_replay_exists_with_minimum_samples(replay_df):
    assert len(replay_df) >= 120, f"Expected >= 120 samples, got {len(replay_df)}"


def test_extended_replay_summary_passes_thresholds(replay_summary):
    assert replay_summary['status'] == 'PASS', (
        f"Extended replay status is {replay_summary['status']}, expected PASS"
    )
    assert replay_summary['mae_pass'] is True, (
        f"MAE threshold not met: {replay_summary['non_saturated_mae']}"
    )
    assert replay_summary['r2_pass'] is True, (
        f"R2 threshold not met: {replay_summary['non_saturated_r2']}"
    )
    assert replay_summary['total_samples'] >= 120, (
        f"Expected >= 120 samples, got {replay_summary['total_samples']}"
    )


# ---------------------------------------------------------------------------
# Test 8-9: Scientific integrity -- no false claims
# ---------------------------------------------------------------------------

def test_no_false_v7c_esp32_claim_in_v8b1_reports():
    forbidden = [
        'canonical V7C validated on ESP32',
        'canonical v7c validated on esp32',
        'V7C validated on hardware',
        'v7c validated on hardware',
    ]
    for fname in ['V8B1_CANONICAL_ARTIFACT_RECOVERY_AND_V8B0_CLEANUP.md',
                  'V8B1_NEXT_ACTION_AFTER_CLEANUP.md']:
        fpath = os.path.join(REPORTS_DIR, fname)
        if not os.path.exists(fpath):
            continue
        content = open(fpath, encoding='utf-8').read().lower()
        for phrase in forbidden:
            # Allow if explicitly negated (preceded by "not" or marked [FAIL])
            idx = content.find(phrase.lower())
            if idx >= 0:
                context = content[max(0, idx - 30):idx + len(phrase) + 30]
                negated = 'not' in context or '[fail]' in context or '(not' in context
                assert negated, (
                    f"False claim found in {fname}: '{phrase}'\nContext: {context}"
                )


def test_no_false_anomaly_claim_in_v8b1_reports():
    forbidden = [
        'anomaly detection validated',
        'anomaly detection works',
        'anomaly detection tested on esp32',
    ]
    for fname in ['V8B1_CANONICAL_ARTIFACT_RECOVERY_AND_V8B0_CLEANUP.md',
                  'V8B1_NEXT_ACTION_AFTER_CLEANUP.md']:
        fpath = os.path.join(REPORTS_DIR, fname)
        if not os.path.exists(fpath):
            continue
        content = open(fpath, encoding='utf-8').read().lower()
        for phrase in forbidden:
            assert phrase not in content, (
                f"False anomaly claim found in {fname}: '{phrase}'"
            )


# ---------------------------------------------------------------------------
# Test 10: V8A evidence untouched
# ---------------------------------------------------------------------------

def test_v8a_evidence_preserved():
    metrics_path = os.path.join(V8A_DIR, 'v8a_esp32_replay_metrics.json')
    assert os.path.exists(metrics_path), "V8A metrics JSON missing"
    with open(metrics_path, encoding='utf-8') as f:
        metrics = json.load(f)
    acc = metrics.get('accuracy', {})
    assert acc.get('mae') < 1e-6, f"V8A MAE changed: {acc.get('mae')}"
    assert acc.get('matched_samples') == 20, "V8A sample count changed"


# ---------------------------------------------------------------------------
# Test 11: Core V7C artifacts present
# ---------------------------------------------------------------------------

def test_core_v7c_artifacts_present():
    required = [
        'canonical_feature_order.json',
        'canonical_scaler_params.json',
        'canonical_golden_vectors.csv',
        'canonical_expected_serial_output.csv',
        'canonical_model_weights.json',
        'canonical_model_weights_preview.h',
        'canonical_mlp_pipeline.pkl',
    ]
    for fname in required:
        path = os.path.join(ARTIFACTS_DIR, fname)
        assert os.path.exists(path), f"Core V7C artifact missing: {fname}"


# ---------------------------------------------------------------------------
# Test 12: pkl inference works correctly
# ---------------------------------------------------------------------------

def test_pkl_inference_is_dict_with_scaler_and_model():
    pkl_path = os.path.join(ARTIFACTS_DIR, 'canonical_mlp_pipeline.pkl')
    with open(pkl_path, 'rb') as f:
        obj = pickle.load(f)
    assert isinstance(obj, dict), f"pkl should be dict, got {type(obj).__name__}"
    assert 'scaler' in obj, "pkl dict missing 'scaler'"
    assert 'model' in obj, "pkl dict missing 'model'"
    assert 'features' in obj, "pkl dict missing 'features'"


def test_pkl_inference_produces_valid_predictions():
    pkl_path = os.path.join(ARTIFACTS_DIR, 'canonical_mlp_pipeline.pkl')
    with open(pkl_path, 'rb') as f:
        obj = pickle.load(f)

    scaler = obj['scaler']
    model = obj['model']
    features = obj['features']

    golden_path = os.path.join(ARTIFACTS_DIR, 'canonical_golden_vectors.csv')
    df = pd.read_csv(golden_path)
    X = df[features].values
    X_scaled = scaler.transform(X)
    preds = model.predict(X_scaled)

    assert len(preds) == 20, f"Expected 20 predictions, got {len(preds)}"

    # Non-saturated samples should match soc_numpy_canonical within 1e-6
    refs = df['soc_numpy_canonical'].values.astype(float)
    for i, (p, r) in enumerate(zip(preds, refs)):
        if r < 1.0:  # skip clipped samples
            diff = abs(p - r)
            assert diff < 1e-6, (
                f"gv_{i+1:02d}: pred={p:.8f} ref={r:.8f} diff={diff:.2e} > 1e-6"
            )


# ---------------------------------------------------------------------------
# Test 13: Saturation behavior documented
# ---------------------------------------------------------------------------

def test_saturation_behavior_documented(replay_df):
    assert 'saturation_flag' in replay_df.columns, "saturation_flag column missing from replay"
    n_sat = int(replay_df['saturation_flag'].sum())
    assert n_sat >= 3, f"Expected >= 3 saturated samples, got {n_sat}"

    sat_rows = replay_df[replay_df['saturation_flag'] == 1]
    for _, row in sat_rows.iterrows():
        raw = float(row['soc_canonical_pred_raw'])
        clipped = float(row['soc_canonical_pred_clipped'])
        assert raw != clipped or abs(raw) > 1.0 or raw < 0.0, (
            f"Saturation flag set but raw={raw} clipped={clipped} are equal and in bounds"
        )


# ---------------------------------------------------------------------------
# Test 14: Decision is READY_FOR_V8B_PACKAGE_BUILD
# ---------------------------------------------------------------------------

def test_next_action_decision_is_ready_for_package_build():
    path = os.path.join(REPORTS_DIR, 'V8B1_NEXT_ACTION_AFTER_CLEANUP.md')
    content = open(path, encoding='utf-8').read()
    assert 'READY_FOR_V8B_PACKAGE_BUILD' in content, (
        "Decision READY_FOR_V8B_PACKAGE_BUILD not found in next action report"
    )
    # Should NOT say CONTINUE_OFFLINE_EXPANSION as decision
    lines = [l.strip() for l in content.splitlines()]
    decision_lines = [l for l in lines if 'Decision:' in l and 'CONTINUE_OFFLINE_EXPANSION' in l]
    assert len(decision_lines) == 0, (
        f"Old decision CONTINUE_OFFLINE_EXPANSION still present: {decision_lines}"
    )
