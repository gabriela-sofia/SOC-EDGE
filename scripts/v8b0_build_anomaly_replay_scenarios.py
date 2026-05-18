#!/usr/bin/env python3
"""
V8B0 -- Build Anomaly Replay Scenarios
Generate 10-15 distinct anomaly scenarios for ESP32 validation.
Includes: voltage spikes, current drops, temperature jumps, flatlines, etc.
"""

import csv
from pathlib import Path
from datetime import datetime


def build_anomaly_scenarios():
    """
    Build anomaly replay dataset.
    Currently: PLACEHOLDER with scenario definitions.
    Full implementation requires:
    1. Baseline samples from Phase 3C
    2. Canonical Python model to generate references
    3. Perturbation rules for each anomaly type
    """

    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "outputs" / "v8b0_post_esp_expansion"

    print("[V8B0] Building anomaly replay scenarios...")
    print(f"[V8B0] Output: {output_dir}")

    # Define 10 anomaly scenarios
    scenarios = [
        {
            "scenario_id": "ano_001_voltage_spike",
            "description": "Sudden +0.5V jump in voltage",
            "anomaly_type": "voltage_spike",
            "perturbation": "voltage_v += 0.5",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "HIGH",
            "scientific_justification": "Battery voltage spike indicates external fault or measurement error"
        },
        {
            "scenario_id": "ano_002_current_spike",
            "description": "Sudden +200 mA jump in current",
            "anomaly_type": "current_spike",
            "perturbation": "current_ma += 200",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "HIGH",
            "scientific_justification": "Current spike indicates short circuit or overload condition"
        },
        {
            "scenario_id": "ano_003_temperature_jump",
            "description": "Sudden +15degC jump in temperature",
            "anomaly_type": "temperature_jump",
            "perturbation": "temperature_c += 15",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "MEDIUM",
            "scientific_justification": "Rapid temperature rise indicates thermal runaway risk"
        },
        {
            "scenario_id": "ano_004_voltage_flatline",
            "description": "Same voltage for 10+ consecutive samples",
            "anomaly_type": "voltage_flatline",
            "perturbation": "voltage_v = constant 4.0",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "MEDIUM",
            "scientific_justification": "Constant voltage with varying current is physically implausible"
        },
        {
            "scenario_id": "ano_005_current_dropout",
            "description": "Sudden drop to 0 mA current",
            "anomaly_type": "current_dropout",
            "perturbation": "current_ma = 0",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "HIGH",
            "scientific_justification": "Abrupt current dropout indicates sensor failure or circuit break"
        },
        {
            "scenario_id": "ano_006_noise_burst",
            "description": "High-frequency oscillation in current",
            "anomaly_type": "noise_burst",
            "perturbation": "current_ma += sin(timestamp * 2pi * 1000) * 50",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "LOW",
            "scientific_justification": "High-frequency noise indicates sensor interference"
        },
        {
            "scenario_id": "ano_007_soc_temporal_incoherence",
            "description": "SOC increases despite negative current (charging backward)",
            "anomaly_type": "soc_incoherence",
            "perturbation": "current_ma = -200, observe SOC prediction",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "MEDIUM",
            "scientific_justification": "SOC should decrease with discharge; increase indicates state error"
        },
        {
            "scenario_id": "ano_008_domain_shift_current_scale",
            "description": "Current suddenly shifted 10x (scale change)",
            "anomaly_type": "domain_shift",
            "perturbation": "current_ma *= 10",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "HIGH",
            "scientific_justification": "Out-of-distribution current scale violates model assumptions"
        },
        {
            "scenario_id": "ano_009_low_voltage_warning",
            "description": "Voltage below critical threshold (< 3.8V)",
            "anomaly_type": "voltage_warning",
            "perturbation": "voltage_v = 3.7",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "MEDIUM",
            "scientific_justification": "Low voltage indicates battery depletion risk"
        },
        {
            "scenario_id": "ano_010_high_temperature_warning",
            "description": "Temperature above critical threshold (> 45degC)",
            "anomaly_type": "temperature_warning",
            "perturbation": "temperature_c = 50",
            "source": "synthetic",
            "expected_flag": 1,
            "severity": "MEDIUM",
            "scientific_justification": "High temperature indicates thermal runaway risk"
        }
    ]

    # Write scenario manifest
    manifest_path = output_dir / "v8b0_anomaly_scenario_manifest.csv"
    with open(manifest_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'scenario_id', 'description', 'anomaly_type', 'perturbation',
            'source', 'expected_flag', 'severity', 'scientific_justification'
        ])
        writer.writeheader()

        for scenario in scenarios:
            writer.writerow(scenario)

    print(f"[V8B0] [OK] Wrote scenario manifest: {manifest_path}")
    print(f"[V8B0]   {len(scenarios)} anomaly scenarios defined")

    # Write expected flags reference
    expected_flags_path = output_dir / "v8b0_anomaly_expected_flags.csv"
    with open(expected_flags_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'scenario_id', 'sample_id_in_batch', 'expected_anomaly_flag',
            'expected_anomaly_code', 'expected_status'
        ])
        writer.writeheader()

        for idx, scenario in enumerate(scenarios):
            writer.writerow({
                'scenario_id': scenario['scenario_id'],
                'sample_id_in_batch': idx,
                'expected_anomaly_flag': scenario['expected_flag'],
                'expected_anomaly_code': idx + 1,  # Code 1-10
                'expected_status': 'ANOMALY' if scenario['expected_flag'] == 1 else 'OK'
            })

    print(f"[V8B0] [OK] Wrote expected flags: {expected_flags_path}")

    # Write placeholder anomaly vectors (to be populated with actual samples)
    anomaly_vectors_path = output_dir / "v8b0_anomaly_replay_scenarios_PLACEHOLDER.csv"
    with open(anomaly_vectors_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'sample_id', 'scenario_id', 'voltage_v', 'temperature_c', 'current_ma',
            'delta_voltage', 'delta_temperature', 'delta_current', 'is_anomalous'
        ])
        writer.writeheader()

        # Placeholder rows: 1 baseline + 10 scenarios
        baseline = {
            'voltage_v': 4.0,
            'temperature_c': 25.0,
            'current_ma': 100.0,
            'delta_voltage': -0.01,
            'delta_temperature': 0.5,
            'delta_current': 50.0
        }

        # Row 0: Baseline (no anomaly)
        writer.writerow({
            'sample_id': 0,
            'scenario_id': 'baseline',
            'voltage_v': baseline['voltage_v'],
            'temperature_c': baseline['temperature_c'],
            'current_ma': baseline['current_ma'],
            'delta_voltage': baseline['delta_voltage'],
            'delta_temperature': baseline['delta_temperature'],
            'delta_current': baseline['delta_current'],
            'is_anomalous': 0
        })

        # Rows 1-10: One per scenario (placeholder values)
        for idx, scenario in enumerate(scenarios):
            writer.writerow({
                'sample_id': idx + 1,
                'scenario_id': scenario['scenario_id'],
                'voltage_v': baseline['voltage_v'] + (0.5 if 'voltage' in scenario['anomaly_type'] else 0),
                'temperature_c': baseline['temperature_c'] + (15 if 'temperature' in scenario['anomaly_type'] else 0),
                'current_ma': baseline['current_ma'] + (200 if 'current' in scenario['anomaly_type'] else 0),
                'delta_voltage': baseline['delta_voltage'],
                'delta_temperature': baseline['delta_temperature'],
                'delta_current': baseline['delta_current'],
                'is_anomalous': 1
            })

    print(f"[V8B0] [OK] Wrote placeholder anomaly vectors: {anomaly_vectors_path}")
    print(f"[V8B0]   [WARNING] PLACEHOLDER: Requires actual sample generation")

    return True


def main():
    print("\n=== V8B0 Anomaly Replay Scenario Builder ===\n")

    success = build_anomaly_scenarios()

    if success:
        print("\n[V8B0] [OK] Anomaly scenarios DEFINED")
        print("[V8B0] Status: 10 scenario types with expected behavior")
        print("[V8B0] [WARNING] Actual sample generation pending")
        return 0

    return 1


if __name__ == '__main__':
    exit(main())
