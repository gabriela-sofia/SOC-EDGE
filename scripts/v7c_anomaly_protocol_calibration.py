"""
V7C — Anomaly Protocol Calibration Script.
Generates canonical anomaly protocol, fault injection matrix, and calibration summary
based on V7A/V7B anomaly engine V4 rules, adjusted for canonical model context.
"""

import csv
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'outputs', 'v7c_canonical_method_b_artifact')
ART_V7 = os.path.join(BASE, 'artifacts', 'edge_v7')

os.makedirs(OUT, exist_ok=True)


def _write_csv(path, rows, fieldnames=None):
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    # --- Anomaly protocol (canonical) ---
    # Based on V7A anomaly engine V4, updated for canonical model
    protocol_rows = [
        {
            'rule_id': 'ANO_C_01',
            'rule_name': 'voltage_spike',
            'category': 'PHYSICAL_ABSOLUTE',
            'trigger_condition': 'voltage_v > 4.30',
            'threshold_value': '4.30',
            'threshold_unit': 'V',
            'threshold_origin': 'TRAINING_RANGE_UPPER + 0.09V safety margin',
            'origin_basis': 'training_range_high=4.21V from canonical scaler; +0.09V same as V7A',
            'detection_method': 'RULE_BASED',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(1) — single comparison',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'NONE — threshold unchanged. Canonical scaler confirms same voltage range.',
            'notes': 'Consistent with V7A ANO_01. ESP32 must validate false positive rate on real sensor.',
        },
        {
            'rule_id': 'ANO_C_02',
            'rule_name': 'voltage_flatline',
            'category': 'TEMPORAL_HEURISTIC',
            'trigger_condition': 'abs(delta_voltage) < 0.001 for N consecutive samples (N=5)',
            'threshold_value': '0.001',
            'threshold_unit': 'V',
            'threshold_origin': 'HEURISTIC — smaller than minimum observed delta_voltage in training',
            'origin_basis': 'training_range delta_voltage: -0.06 to 0.02V',
            'detection_method': 'SLIDING_WINDOW',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(N) buffer — 5 samples',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'NONE — flatline logic unchanged',
            'notes': 'Flatline detection requires multi-sample buffer on ESP32. Only detects transition — sustained flatline not flagged every cycle (V7A design).',
        },
        {
            'rule_id': 'ANO_C_03',
            'rule_name': 'current_spike',
            'category': 'PHYSICAL_ABSOLUTE',
            'trigger_condition': 'current_ma > 340.0',
            'threshold_value': '340.0',
            'threshold_unit': 'mA',
            'threshold_origin': 'TRAINING_RANGE_UPPER + 13.7mA safety margin',
            'origin_basis': 'training_range_high=326.3mA; +13.7mA = +4.2% margin',
            'detection_method': 'RULE_BASED',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(1) — single comparison',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'NONE — threshold unchanged. Canonical confirms mA units.',
            'notes': 'CRITICAL: threshold is in mA. If firmware feeds Amperes, this will never trigger.',
        },
        {
            'rule_id': 'ANO_C_04',
            'rule_name': 'current_dropout',
            'category': 'TEMPORAL_HEURISTIC',
            'trigger_condition': 'current_ma < 5.0 while previously active (>50mA)',
            'threshold_value': '5.0',
            'threshold_unit': 'mA',
            'threshold_origin': 'HEURISTIC — below minimum discharge current in training (50.1mA)',
            'origin_basis': 'training_range_low=50.1mA; threshold=5.0mA as likely sensor dropout',
            'detection_method': 'RULE_BASED',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(1)',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'NONE',
            'notes': 'Dropout only detectable at transition. Sustained zero current = ESP32 sampling issue or end of discharge.',
        },
        {
            'rule_id': 'ANO_C_05',
            'rule_name': 'temperature_jump',
            'category': 'PHYSICAL_ABSOLUTE',
            'trigger_condition': 'temperature_c > 45.0 OR temperature_c < -5.0',
            'threshold_value': '45.0 / -5.0',
            'threshold_unit': 'C',
            'threshold_origin': 'PHYSICAL_SAFETY — beyond cell safe operating range',
            'origin_basis': 'training_range: 9.41-40.19C; safe operating margins +5C/-14.41C',
            'detection_method': 'RULE_BASED',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(1)',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'NONE',
            'notes': 'temperature_c included in canonical model (V2 excluded it). Temperature anomaly detection unchanged.',
        },
        {
            'rule_id': 'ANO_C_06',
            'rule_name': 'soc_temporal_incoherence',
            'category': 'SOC_TEMPORAL',
            'trigger_condition': 'abs(soc[t] - soc[t-1]) > 0.20 in single step',
            'threshold_value': '0.20',
            'threshold_unit': 'SOC_fraction',
            'threshold_origin': 'HEURISTIC — maximum plausible SOC change per sample (1 min interval)',
            'origin_basis': 'At 326.3mA max current, 1-min step drains < 5mAh. Q_total ~30mAh => max delta_SOC < 0.17. Threshold 0.20 adds margin.',
            'detection_method': 'TEMPORAL_DELTA',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(1) — compare current vs previous SOC',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'MINOR — threshold unchanged; note updated for canonical model clarity',
            'notes': 'Flags model instability or sensor transient. Canonical model same temporal behavior as V1.',
        },
        {
            'rule_id': 'ANO_C_07',
            'rule_name': 'noise_burst',
            'category': 'SIGNAL_QUALITY',
            'trigger_condition': 'std(voltage_v over 5 samples) > 0.05',
            'threshold_value': '0.05',
            'threshold_unit': 'V',
            'threshold_origin': 'HEURISTIC — higher than expected voltage noise in clean IoT signal',
            'origin_basis': 'Clean IoT voltage std typically < 0.01V. 0.05V = 5x expected noise.',
            'detection_method': 'SLIDING_WINDOW_STD',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(N) — 5-sample rolling std',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'NONE',
            'notes': 'Requires 5-sample buffer. Not recommended for high-frequency sampling (> 1 Hz).',
        },
        {
            'rule_id': 'ANO_C_08',
            'rule_name': 'domain_shift_current_scale',
            'category': 'DOMAIN_SHIFT',
            'trigger_condition': 'current_ma < 10.0 OR current_ma > 350.0 (non-zero)',
            'threshold_value': '10.0 / 350.0',
            'threshold_unit': 'mA',
            'threshold_origin': 'TRAINING_RANGE_BOUNDS with safety margin',
            'origin_basis': 'training_range: 50.1-326.3mA. Lower bound 10mA indicates unit error (Amperes?). Upper 350mA > training max.',
            'detection_method': 'RULE_BASED',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(1)',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'NOTE_ADDED — lower bound 10mA specifically designed to detect Ampere unit confusion (0.05A = 50mA, 0.01A = 10mA)',
            'notes': 'Primary guard against unit error. If current_ma < 10, likely firmware is feeding Amperes (e.g. 0.05A instead of 50mA).',
        },
        {
            'rule_id': 'ANO_C_09',
            'rule_name': 'thermal_composite',
            'category': 'COMPOSITE_THERMAL',
            'trigger_condition': 'temperature_c > 40.0 AND current_ma > 280.0',
            'threshold_value': '40.0C + 280.0mA',
            'threshold_unit': 'composite',
            'threshold_origin': 'TRAINING_RANGE — near-max temp and near-max current simultaneously',
            'origin_basis': 'temp_max=40.19C; current_max=326.3mA. High temp AND high current = stress condition.',
            'detection_method': 'COMPOSITE_RULE',
            'requires_esp_validation': 'true',
            'expected_runtime_cost': 'O(1) — two comparisons AND',
            'status': 'FROZEN_CANDIDATE',
            'canonical_change_vs_v7a': 'NONE',
            'notes': 'Canonical model retains temperature_c (unlike V2). This rule is more meaningful with temperature_c in model.',
        },
    ]
    protocol_path = os.path.join(OUT, 'v7c_anomaly_protocol.csv')
    _write_csv(protocol_path, protocol_rows)
    print('[V7C_ANOMALY] Wrote:', protocol_path)

    # --- Fault injection matrix ---
    fault_rows = [
        {'scenario': 'voltage_spike', 'rule_triggered': 'ANO_C_01', 'expected_detection': 'YES',
         'injection_method': 'voltage_v = 4.50V (above 4.30 threshold)',
         'expected_flag_rate': '1.0', 'category': 'PHYSICAL_ABSOLUTE',
         'v7a_result': '1.0 (100%)', 'canonical_change': 'NONE', 'status': 'PREDICTED_PASS'},
        {'scenario': 'current_spike', 'rule_triggered': 'ANO_C_03', 'expected_detection': 'YES',
         'injection_method': 'current_ma = 400.0 (above 340.0 threshold)',
         'expected_flag_rate': '1.0', 'category': 'PHYSICAL_ABSOLUTE',
         'v7a_result': '1.0 (100%)', 'canonical_change': 'NONE', 'status': 'PREDICTED_PASS'},
        {'scenario': 'temperature_jump', 'rule_triggered': 'ANO_C_05', 'expected_detection': 'YES',
         'injection_method': 'temperature_c = 55.0C (above 45.0 threshold)',
         'expected_flag_rate': '1.0', 'category': 'PHYSICAL_ABSOLUTE',
         'v7a_result': '1.0 (100%)', 'canonical_change': 'NONE', 'status': 'PREDICTED_PASS'},
        {'scenario': 'voltage_flatline', 'rule_triggered': 'ANO_C_02', 'expected_detection': 'PARTIAL',
         'injection_method': 'delta_voltage = 0.0 sustained for 10+ samples',
         'expected_flag_rate': '0.1', 'category': 'TEMPORAL_HEURISTIC',
         'v7a_result': '0.1 (10% — only transition detected)', 'canonical_change': 'NONE', 'status': 'PREDICTED_PARTIAL'},
        {'scenario': 'current_dropout', 'rule_triggered': 'ANO_C_04', 'expected_detection': 'PARTIAL',
         'injection_method': 'current_ma = 0.0 sustained for 10+ samples',
         'expected_flag_rate': '0.1', 'category': 'TEMPORAL_HEURISTIC',
         'v7a_result': '0.1 (10% — only transition detected)', 'canonical_change': 'NONE', 'status': 'PREDICTED_PARTIAL'},
        {'scenario': 'noise_burst', 'rule_triggered': 'ANO_C_07', 'expected_detection': 'YES',
         'injection_method': 'voltage_v noise std = 0.08V (above 0.05 threshold)',
         'expected_flag_rate': '0.8', 'category': 'SIGNAL_QUALITY',
         'v7a_result': '0.8 (80% — rolling window coverage)', 'canonical_change': 'NONE', 'status': 'PREDICTED_PASS'},
        {'scenario': 'soc_temporal_incoherence', 'rule_triggered': 'ANO_C_06', 'expected_detection': 'YES',
         'injection_method': 'synthetic SOC jump > 0.25 between consecutive samples',
         'expected_flag_rate': '1.0', 'category': 'SOC_TEMPORAL',
         'v7a_result': '1.0 (100%)', 'canonical_change': 'MINOR — canonical model may have different SOC dynamics', 'status': 'PREDICTED_PASS'},
        {'scenario': 'domain_shift_current_scale', 'rule_triggered': 'ANO_C_08', 'expected_detection': 'PARTIAL',
         'injection_method': 'current_ma = 0.05 (simulating Ampere unit error — 50mA fed as 0.05A)',
         'expected_flag_rate': '1.0', 'category': 'DOMAIN_SHIFT',
         'v7a_result': '0.1 (10% in V7A)', 'canonical_change': 'THRESHOLD_LOWERED to 10mA — now detects Ampere error at 0.05A=50mA', 'status': 'PREDICTED_IMPROVED'},
        {'scenario': 'thermal_composite', 'rule_triggered': 'ANO_C_09', 'expected_detection': 'YES',
         'injection_method': 'temperature_c=42C AND current_ma=290mA simultaneously',
         'expected_flag_rate': '1.0', 'category': 'COMPOSITE_THERMAL',
         'v7a_result': 'N/A — composite rule added in V7C', 'canonical_change': 'NEW_RULE in V7C (temperature retained in canonical)', 'status': 'PREDICTED_PASS'},
    ]
    fault_path = os.path.join(OUT, 'v7c_fault_injection_matrix.csv')
    _write_csv(fault_path, fault_rows)
    print('[V7C_ANOMALY] Wrote:', fault_path)

    # --- Calibration summary JSON ---
    summary = {
        'version': 'v7c',
        'date': '2026-05-15',
        'n_rules': len(protocol_rows),
        'rules_inherited_from_v7a': 8,
        'rules_new_in_v7c': 1,
        'new_rules': ['ANO_C_09 thermal_composite — enabled by temperature_c retention in canonical model'],
        'all_rules_status': 'FROZEN_CANDIDATE — require ESP32 validation before production',
        'n_fault_scenarios': len(fault_rows),
        'physical_absolute_scenarios': 3,
        'predicted_100_pct_detection': ['voltage_spike', 'current_spike', 'temperature_jump',
                                        'soc_temporal_incoherence', 'thermal_composite', 'domain_shift_current_scale'],
        'predicted_partial_detection': ['voltage_flatline', 'current_dropout'],
        'improvements_vs_v7a': [
            'domain_shift_current_scale threshold lowered from ~50mA to 10mA — better Ampere unit error detection',
            'New thermal_composite rule (ANO_C_09) added — possible because canonical retains temperature_c',
        ],
        'not_yet_validated': [
            'No fault injection has been run with canonical model yet — predictions only',
            'ESP32 real-time anomaly detection latency not measured',
            'False positive rate on normal IoT data not measured',
        ],
    }
    cal_summary_path = os.path.join(OUT, 'v7c_anomaly_calibration_summary.json')
    with open(cal_summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print('[V7C_ANOMALY] Wrote:', cal_summary_path)

    return summary


if __name__ == '__main__':
    result = main()
    print('[V7C_ANOMALY] Done. {} rules, {} fault scenarios.'.format(
        result['n_rules'], result['n_fault_scenarios']))
