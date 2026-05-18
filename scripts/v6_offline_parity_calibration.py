#!/usr/bin/env python3
"""
V6 — Offline Parity & Calibration Audit

Objetivo: Auditoria científica offline da paridade entre:
- Pipeline V2-V5 (Python)
- Futura execução embarcada (ESP32)

Sem tocar na ESP32 ainda. Apenas documentar estado de prontidão offline.
"""

import json
import csv
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def safe_read_csv(path: str, limit: int = None) -> List[Dict]:
    """Read CSV safely, return list of dicts."""
    if not os.path.exists(path):
        return []
    try:
        data = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                data.append(row)
        return data
    except Exception as e:
        return []

def safe_read_json(path: str) -> Dict:
    """Read JSON safely, return dict."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {}

def load_v_history() -> Dict[str, Any]:
    """Load summaries from V2, V3, V4, V5."""
    history = {
        'v2': safe_read_json(r'outputs/offline_soc_validation/v2/summary_v2.json'),
        'v3': safe_read_json(r'outputs/offline_soh_integration/v3/summary_v3.json'),
        'v4': safe_read_json(r'outputs/offline_anomaly/v4/summary_v4.json'),
        'v5': safe_read_json(r'outputs/offline_deep_anomaly/v5/summary_v5.json'),
    }
    return history

def load_v2_metrics() -> List[Dict]:
    """Load V2 benchmark results."""
    return safe_read_csv(r'outputs/offline_soc_validation/v2/soc_benchmark_results_v2.csv')

def load_v4_anomaly_metrics() -> List[Dict]:
    """Load V4 anomaly scenario results."""
    return safe_read_csv(r'outputs/offline_anomaly/v4/anomaly_by_scenario_metrics_v4.csv')

def summarize_v2_results(metrics: List[Dict]) -> Dict:
    """Summarize V2 SOC benchmark results."""
    if not metrics:
        return {'status': 'MISSING_INPUTS', 'reason': 'V2 metrics not found'}

    valid_results = [m for m in metrics if m.get('r2') and m['r2'] != '']
    errors = [m for m in metrics if 'ERROR' in str(m.get('note', ''))]

    if valid_results:
        r2_values = [float(m['r2']) for m in valid_results if m.get('r2')]
        mae_values = [float(m['mae']) for m in valid_results if m.get('mae')]

        return {
            'status': 'LOADED',
            'total_splits': len(metrics),
            'valid_splits': len(valid_results),
            'error_splits': len(errors),
            'mean_r2': round(sum(r2_values) / len(r2_values), 5),
            'best_r2': round(max(r2_values), 5),
            'worst_r2': round(min(r2_values), 5),
            'mean_mae': round(sum(mae_values) / len(mae_values), 5) if mae_values else 0,
            'dominant_feature': 'voltage_V (>99.9% importance)',
        }
    return {'status': 'INVALID', 'reason': 'No valid results found'}

def summarize_v4_anomaly(metrics: List[Dict]) -> Dict:
    """Summarize V4 anomaly results."""
    if not metrics:
        return {'status': 'MISSING_INPUTS', 'reason': 'V4 metrics not found'}

    scenarios = set()
    f1_scores = []

    for m in metrics:
        if m.get('scenario'):
            scenarios.add(m['scenario'])
        if m.get('f1') and m['f1'] != '':
            try:
                f1_scores.append(float(m['f1']))
            except:
                pass

    return {
        'status': 'LOADED',
        'total_scenarios': len(scenarios),
        'scenarios': list(scenarios),
        'mean_f1': round(sum(f1_scores) / len(f1_scores), 4) if f1_scores else 0,
        'best_f1': round(max(f1_scores), 4) if f1_scores else 0,
        'worst_f1': round(min(f1_scores), 4) if f1_scores else 0,
    }

def assess_scaler_status() -> Dict[str, Any]:
    """Assess if scaler is frozen (current: NO)."""
    return {
        'scaler_frozen': False,
        'scaler_path': None,
        'reason': 'No scaler dumped yet; V2-V5 used sklearn default normalization',
        'impact': 'ESP32 will need to replicate exact normalization from Python pipeline',
        'recommendation': 'Freeze scaler in V7 before TFLite export',
    }

def assess_domain_shift() -> Dict[str, Any]:
    """Assess known domain shift issues from V2."""
    return {
        'oxford_to_mcmaster_r2': 0.10436,
        'oxford_to_mcmaster_status': 'FAILS',
        'mcmaster_to_oxford_r2': 0.88946,
        'mcmaster_to_oxford_status': 'ACCEPTABLE',
        'current_shift_normalized': 812.9,
        'temperature_shift_normalized': 15.9,
        'root_cause': 'Oxford constant current (0.72A) vs McMaster dynamic (0-18A)',
        'solution_status': 'OPEN — domain adaptation not implemented',
    }

def assess_esp32_readiness() -> Dict[str, Any]:
    """Assess ESP32 readiness based on V4."""
    return {
        'rules_feasible_high': 8,
        'rules_feasible_medium': 3,
        'rules_feasible_low': 4,
        'rules_not_feasible': 0,
        'rules_ready_now': [
            'voltage_physical_range',
            'temperature_physical_range',
            'current_physical_range',
            'abrupt_voltage_deviation',
            'abrupt_temperature_deviation',
            'thermal_risk',
            'soc_temporal_consistency',
            'abrupt_current_deviation',
        ],
        'blockers': [
            'No formal parity Python↔C',
            'No TFLite conversion tested',
            'No real-world deployment tested',
        ],
    }

def build_parity_table(history: Dict) -> List[Dict]:
    """Build summary parity table comparing versions."""
    return [
        {
            'version': 'V1.1',
            'phase': 'Auditoria metodológica',
            'datasets': 'Oxford (8 cells)',
            'samples': '1,459,613',
            'target': 'Method B (frozen)',
            'status': 'PASS',
        },
        {
            'version': 'V2',
            'phase': 'Validação SOC',
            'datasets': 'Oxford + McMaster',
            'samples': '1.46M + 4.83M',
            'metrics_available': True,
            'best_r2': 0.99873,
            'worst_r2': -11.52,
            'domain_shift': 'HIGH (current 812×)',
            'status': 'PARTIAL_READY',
        },
        {
            'version': 'V3',
            'phase': 'Integração SOH',
            'datasets': 'PoliMi (2 cells)',
            'samples': '200,509',
            'metrics_available': True,
            'best_soh_r2': 0.9866,
            'worst_soh_r2': -7.86,
            'cells_evaluated': 2,
            'status': 'PARTIAL_READY',
        },
        {
            'version': 'V4',
            'phase': 'Engine de anomalias',
            'datasets': 'Sintético + Oxford/McMaster/PoliMi',
            'rules': 15,
            'esp32_feasible': 8,
            'synthetic_scenarios': 15,
            'mean_f1': 0.198,
            'labels_real': False,
            'status': 'PARTIAL_READY',
        },
        {
            'version': 'V5',
            'phase': 'Deep anomaly',
            'datasets': 'Sintético + Oxford/McMaster/PoliMi',
            'models_tested': 6,
            'best_model': 'LSTM AE',
            'best_auroc': 0.759,
            'labels_real': False,
            'esp32_feasible': 'LOW (TFLite future)',
            'status': 'PARTIAL_READY',
        },
    ]

def generate_missing_inputs_report(history: Dict) -> List[Dict]:
    """Identify what's missing for full V6 readiness."""
    missing = [
        {
            'input_type': 'Scaler frozen state',
            'current_state': 'Not frozen',
            'needed_for': 'ESP32 parity replication',
            'blocker': 'V7',
        },
        {
            'input_type': 'Real fault labels',
            'current_state': 'Only synthetic (V4/V5)',
            'needed_for': 'Validation of anomaly detection',
            'blocker': 'V8 field data',
        },
        {
            'input_type': 'Domain adaptation solution',
            'current_state': 'Open (Oxford→McMaster R²=0.104)',
            'needed_for': 'Cross-domain model generalization',
            'blocker': 'V7+ research',
        },
        {
            'input_type': 'TFLite export validation',
            'current_state': 'Not tested',
            'needed_for': 'ESP32 deployment of models',
            'blocker': 'V7',
        },
        {
            'input_type': 'Formal parity test Python↔C',
            'current_state': 'Does not exist',
            'needed_for': 'Validate firmware anomaly rules',
            'blocker': 'V6→V7',
        },
        {
            'input_type': 'PoliMi SOC predictions',
            'current_state': 'V2 model not applicable to PoliMi chemistry',
            'needed_for': 'Complete SOC+SOH integration',
            'blocker': 'V3 unresolved',
        },
    ]
    return missing

def generate_calibration_thresholds() -> List[Dict]:
    """Calibration thresholds derived from V2/V4."""
    return [
        {
            'parameter': 'voltage_V_min',
            'value': 2.5,
            'source': 'LG HE4 spec + IEC 61960',
            'type': 'physical_absolute',
            'confidence': 'HIGH',
            'domain_applicability': 'All',
        },
        {
            'parameter': 'voltage_V_max',
            'value': 4.25,
            'source': 'LG HE4 spec + IEC 61960',
            'type': 'physical_absolute',
            'confidence': 'HIGH',
            'domain_applicability': 'All',
        },
        {
            'parameter': 'temperature_C_min',
            'value': -20,
            'source': 'IEC 61960 / safe operating',
            'type': 'physical_absolute',
            'confidence': 'MEDIUM',
            'domain_applicability': 'All',
        },
        {
            'parameter': 'temperature_C_max',
            'value': 60,
            'source': 'IEC 61960 / safe operating',
            'type': 'physical_absolute',
            'confidence': 'MEDIUM',
            'domain_applicability': 'All',
        },
        {
            'parameter': 'current_A_max',
            'value': 20.0,
            'source': 'LG HE4 datasheet max',
            'type': 'physical_absolute',
            'confidence': 'HIGH',
            'domain_applicability': 'All',
        },
        {
            'parameter': 'delta_voltage_p95',
            'value': 0.679,
            'source': 'Percentile 95 (Oxford+McMaster normal)',
            'type': 'statistical_percentile',
            'confidence': 'MEDIUM',
            'domain_applicability': 'Oxford/McMaster',
            'note': 'PoliMi not included — different cycling profile',
        },
        {
            'parameter': 'delta_current_p95',
            'value': 3.53,
            'source': 'Percentile 95 (Oxford+McMaster normal)',
            'type': 'statistical_percentile',
            'confidence': 'MEDIUM',
            'domain_applicability': 'Oxford/McMaster',
            'note': 'McMaster dominant due to dynamic profiles',
        },
        {
            'parameter': 'delta_temp_p95',
            'value': 9.3,
            'source': 'Percentile 95 (Oxford+McMaster normal)',
            'type': 'statistical_percentile',
            'confidence': 'MEDIUM',
            'domain_applicability': 'Oxford/McMaster',
        },
        {
            'parameter': 'soc_residual_p95',
            'value': 0.134,
            'source': 'Percentile 95 (V2 validation residual)',
            'type': 'model_residual_percentile',
            'confidence': 'LOW',
            'domain_applicability': 'Oxford only',
            'note': 'Not valid cross-domain due to Oxford→McMaster failure',
        },
        {
            'parameter': 'soc_temporal_jump_max',
            'value': 0.05,
            'source': 'V4 heuristic threshold',
            'type': 'temporal_constraint',
            'confidence': 'MEDIUM',
            'domain_applicability': 'All',
            'reason': 'Catch abrupt SOC changes between samples',
        },
    ]

def generate_scientific_readiness_summary() -> Dict[str, Any]:
    """High-level readiness assessment for V6."""
    return {
        'version': 'V6',
        'date': datetime.now().isoformat(),
        'phase': 'Offline Parity & Calibration',
        'project_note': 'NOT a TCC',

        'offline_state': {
            'method_b_locked': True,
            'v2_v3_v4_v5_outputs_available': True,
            'scaler_frozen': False,
            'domain_shift_quantified': True,
            'anomaly_rules_specified': True,
            'deep_models_trained': True,
        },

        'blocker_status': {
            'cell3_cell8_nan': 'OPEN (V2)',
            'mcmaster_loto_0c_failure': 'OPEN (V2)',
            'oxford_to_mcmaster_domain_shift': 'OPEN (V2/V3)',
            'real_fault_labels': 'OPEN (V4/V5 synthetic only)',
            'python_esp32_parity': 'NOT_STARTED (V6→V7)',
            'tflite_conversion': 'NOT_TESTED (V7 plan)',
        },

        'readiness_for_esp32': {
            'rules_ready_now': 8,
            'estimated_ram_8_rules_bytes': '~2KB',
            'estimated_latency_per_sample_us': '~100-500',
            'feasibility': 'MEDIUM (rules only, no ML yet)',
            'ml_models_feasible': {
                'pca_reconstruction': 'LOW (36 floats, viable)',
                'densae': 'LOW (461 params, ~20-30 KB TFLite)',
                'lstmae': 'NOT_FEASIBLE (requires TFLite + buffer)',
            },
        },

        'next_steps_immediate': {
            'v6': 'This phase: offline parity audit + calibration freeze',
            'v7': 'Export SOC MLP to TFLite + freeze scaler',
            'v7': 'Domain adaptation framework or mitigation (open research)',
            'v8': 'Replay serial/digital with stream V/I/T',
            'v9': 'Benchmark on real ESP32: RAM/Flash/latency',
            'v10': 'Anomaly rules embarcadas com persistência temporal',
            'v11': 'Documentação final TCC/artigo',
        },

        'scientific_claims_v6': [
            'Method B is a physically interpretable SOC target based on Coulomb counting normalized by cycle capacity',
            'Models trained in Oxford (constant current) fail to generalize to McMaster (dynamic profiles) due to 812× domain shift in current',
            'Voltage is the dominant feature for SOC estimation (>99.9% importance in V2 RF)',
            'V4 anomaly rules are interpretable but have high false positive rate (10% FPR @ p95)',
            'V5 LSTM captures temporal patterns that V4 rules do not (AUROC 0.759 vs 0.506)',
            'All anomaly labels in V4/V5 are synthetic; no real fault validation performed',
        ],

        'what_v6_cannot_claim': [
            'Method B is better than OCV or Kalman — not compared formally',
            'Domain adaptation is solved — shift quantified but solution not implemented',
            'Anomalies can be detected in field — labels only synthetic, no real faults observed',
            'ESP32 can run V4+V5 — no parity testing or firmware implementation done',
            'SOH can be reliably predicted — only 2 cells, LOCO statistically weak',
            'Cross-domain model exists — Oxford→McMaster R² = 0.104 (failure)',
        ],
    }

def main():
    """Main V6 execution."""
    print("[V6] Offline Parity & Calibration Audit")
    print("=" * 70)

    # Create output directories
    output_dir = Path('outputs/v6_offline_parity_calibration')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load history
    print("Loading V2-V5 summaries...")
    history = load_v_history()

    # Load metrics
    print("Loading V2 SOC metrics...")
    v2_metrics = load_v2_metrics()

    print("Loading V4 anomaly metrics...")
    v4_metrics = load_v4_anomaly_metrics()

    # Generate reports
    print("Generating parity audit...")

    v2_summary = summarize_v2_results(v2_metrics)
    v4_summary = summarize_v4_anomaly(v4_metrics)
    scaler_status = assess_scaler_status()
    domain_shift = assess_domain_shift()
    esp32_status = assess_esp32_readiness()
    parity_table = build_parity_table(history)
    missing_inputs = generate_missing_inputs_report(history)
    thresholds = generate_calibration_thresholds()
    readiness = generate_scientific_readiness_summary()

    # Write parity summary JSON
    parity_summary = {
        'version': 'v6',
        'date': datetime.now().isoformat(),
        'v2_soc_summary': v2_summary,
        'v4_anomaly_summary': v4_summary,
        'scaler_status': scaler_status,
        'domain_shift': domain_shift,
        'esp32_readiness': esp32_status,
        'parity_table': parity_table,
        'scientific_readiness': readiness,
    }

    with open(output_dir / 'v6_parity_summary.json', 'w', encoding='utf-8') as f:
        json.dump(parity_summary, f, indent=2)
    print("[OK] {}".format(output_dir / 'v6_parity_summary.json'))

    # Write parity table CSV
    if parity_table:
        keys = set()
        for row in parity_table:
            keys.update(row.keys())

        with open(output_dir / 'v6_parity_table.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(keys))
            writer.writeheader()
            writer.writerows(parity_table)
    print("[OK] {}".format(output_dir / 'v6_parity_table.csv'))

    # Write calibration thresholds CSV
    if thresholds:
        keys = set()
        for row in thresholds:
            keys.update(row.keys())
        with open(output_dir / 'v6_calibration_thresholds.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(keys), restval='')
            writer.writeheader()
            writer.writerows(thresholds)
    print("[OK] {}".format(output_dir / 'v6_calibration_thresholds.csv'))

    # Write missing inputs CSV
    if missing_inputs:
        keys = set()
        for row in missing_inputs:
            keys.update(row.keys())
        with open(output_dir / 'v6_missing_inputs.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(keys), restval='')
            writer.writeheader()
            writer.writerows(missing_inputs)
    print("[OK] {}".format(output_dir / 'v6_missing_inputs.csv'))

    # Write scientific readiness markdown
    readiness_md = f"""# V6 Scientific Readiness Assessment

**Date:** {readiness['date']}
**Phase:** {readiness['phase']}
**Project:** SOC/SOH/Anomalias para baterias em IoT/Edge AI/TinyML
**Note:** NOT a TCC

## Offline State Summary

- Method B locked: {readiness['offline_state']['method_b_locked']}
- V2-V5 outputs available: {readiness['offline_state']['v2_v3_v4_v5_outputs_available']}
- Scaler frozen: {readiness['offline_state']['scaler_frozen']}
- Domain shift quantified: {readiness['offline_state']['domain_shift_quantified']}
- Anomaly rules specified: {readiness['offline_state']['anomaly_rules_specified']}
- Deep models trained: {readiness['offline_state']['deep_models_trained']}

## Blocker Status

{chr(10).join([f"- {k}: {v}" for k, v in readiness['blocker_status'].items()])}

## ESP32 Readiness

Rules ready now: {readiness['readiness_for_esp32']['rules_ready_now']}
Estimated RAM: {readiness['readiness_for_esp32']['estimated_ram_8_rules_bytes']}
Estimated latency: {readiness['readiness_for_esp32']['estimated_latency_per_sample_us']}
Feasibility: {readiness['readiness_for_esp32']['feasibility']}

## Scientific Claims Made in V6

{chr(10).join([f"- {claim}" for claim in readiness['scientific_claims_v6']])}

## What V6 Cannot Claim

{chr(10).join([f"- {claim}" for claim in readiness['what_v6_cannot_claim']])}

## Next Steps

V6: Offline parity audit + calibration freeze (CURRENT)
V7: TFLite export + scaler freeze + domain adaptation plan
V8: Field replay + real-world validation
V9: ESP32 benchmark
V10: Anomaly rules embarcadas
V11: Documentation final

---

Arquivo produzido por `scripts/v6_offline_parity_calibration.py`.
"""

    with open(output_dir / 'v6_scientific_readiness.md', 'w', encoding='utf-8') as f:
        f.write(readiness_md)
    print("[OK] {}".format(output_dir / 'v6_scientific_readiness.md'))

    print("=" * 70)
    print("[V6] Audit complete.")
    print("Output directory: {}".format(output_dir))
    print("Files created: 5")

    return output_dir

if __name__ == '__main__':
    output_path = main()
