#!/usr/bin/env python3
"""
V8A — ESP32 V7B Replay Validation Ingestion and Metrics Calculation
Ingest raw ESP32 serial log, extract final sample records, compare against
reference, and compute accuracy + resource metrics.
"""

import re
import json
import csv
from pathlib import Path
from statistics import mean, stdev
from typing import List, Tuple, Dict


def read_serial_log(log_path: str) -> List[str]:
    """Read ESP32 serial log and return non-debug, non-boot lines."""
    with open(log_path, 'r') as f:
        lines = f.readlines()

    result = []
    for line in lines:
        line = line.strip()
        # Skip empty lines, DEBUG lines, boot messages
        if not line:
            continue
        if line.startswith('DEBUG_'):
            continue
        if 'rst:' in line or 'POWERON_RESET' in line or 'boot:' in line:
            continue
        if 'configsip:' in line or 'clk_drv:' in line or 'load:' in line:
            continue
        if 'entry 0x' in line or 'READY' in line or 'ets Jul' in line:
            continue
        if 'mode:' in line and 'DIO' in line:
            continue
        result.append(line)

    return result


def parse_sample_record(line: str) -> Tuple[bool, Dict]:
    """
    Parse a sample record line.
    Expected format: sample_id,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap
    Returns (success, dict_or_error)
    """
    parts = line.split(',')

    # Must have exactly 6 fields
    if len(parts) != 6:
        return False, {"error": f"Expected 6 fields, got {len(parts)}: {line}"}

    try:
        sample_id = int(parts[0])
        soc_final = float(parts[1])
        inference_time_ms = float(parts[2])
        free_heap = int(parts[3])
        min_free_heap = int(parts[4])
        max_alloc_heap = int(parts[5])

        return True, {
            "sample_id": sample_id,
            "soc_esp32": soc_final,
            "inference_time_ms": inference_time_ms,
            "free_heap": free_heap,
            "min_free_heap": min_free_heap,
            "max_alloc_heap": max_alloc_heap,
        }
    except (ValueError, IndexError) as e:
        return False, {"error": f"Parse error: {str(e)}", "line": line}


def read_reference(ref_path: str) -> Dict[int, float]:
    """Read reference CSV and return dict of {sample_id: soc_reference}."""
    ref = {}
    with open(ref_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sample_id = int(row['sample_id'])
            soc_ref = float(row['soc_reference_v7b'])
            ref[sample_id] = soc_ref
    return ref


def calculate_metrics(samples: List[Dict], reference: Dict) -> Dict:
    """Calculate MAE, RMSE, R², max AE, and bias."""
    if not samples:
        return {}

    matched = []
    errors = []
    predictions = []
    actuals = []

    for sample in samples:
        sid = sample['sample_id']
        if sid not in reference:
            continue

        pred = sample['soc_esp32']
        actual = reference[sid]
        error = abs(pred - actual)

        matched.append(sid)
        errors.append(error)
        predictions.append(pred)
        actuals.append(actual)

    if not matched:
        return {"error": "No matching samples found"}

    mae = mean(errors)
    rmse = (sum(e**2 for e in errors) / len(errors))**0.5
    max_ae = max(errors)

    # R² calculation
    mean_actual = mean(actuals)
    ss_tot = sum((a - mean_actual)**2 for a in actuals)
    ss_res = sum((p - a)**2 for p, a in zip(predictions, actuals))
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    # Bias: mean(pred - actual)
    bias = mean(p - a for p, a in zip(predictions, actuals))

    return {
        "matched_samples": len(matched),
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "max_absolute_error": max_ae,
        "bias": bias,
    }


def calculate_resource_metrics(samples: List[Dict]) -> Dict:
    """Calculate latency and heap statistics."""
    if not samples:
        return {}

    latencies_ms = [s['inference_time_ms'] for s in samples]
    latencies_us = [s['inference_time_ms'] * 1000 for s in samples]
    heaps_free = [s['free_heap'] for s in samples]
    heaps_min = [s['min_free_heap'] for s in samples]
    heaps_max_alloc = [s['max_alloc_heap'] for s in samples]

    return {
        "latency_mean_ms": mean(latencies_ms),
        "latency_min_ms": min(latencies_ms),
        "latency_max_ms": max(latencies_ms),
        "latency_mean_us": mean(latencies_us),
        "latency_min_us": min(latencies_us),
        "latency_max_us": max(latencies_us),
        "free_heap_bytes": heaps_free[-1] if heaps_free else None,
        "min_free_heap_bytes": min(heaps_min),
        "max_alloc_heap_bytes": max(heaps_max_alloc),
        "num_samples": len(samples),
    }


def main():
    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / "outputs" / "v8a_esp32_v7b_replay_validation" / "raw"
    out_dir = base_dir / "outputs" / "v8a_esp32_v7b_replay_validation"

    # Paths
    log_path = raw_dir / "esp32_serial_log_run1_v7b.txt"
    ref_path = raw_dir / "serial_replay_reference_v7b_compatible.csv"

    # Read and parse
    print(f"[V8A] Reading serial log: {log_path}")
    lines = read_serial_log(str(log_path))
    print(f"[V8A] Extracted {len(lines)} non-debug lines")

    samples = []
    parse_errors = []

    for i, line in enumerate(lines):
        success, data = parse_sample_record(line)
        if success:
            samples.append(data)
        else:
            parse_errors.append((i, data))

    print(f"[V8A] Parsed {len(samples)} valid sample records")
    if parse_errors:
        print(f"[V8A] Parse errors: {len(parse_errors)}")
        for idx, err in parse_errors[:5]:
            print(f"  Line {idx}: {err}")

    # Read reference
    print(f"[V8A] Reading reference: {ref_path}")
    reference = read_reference(str(ref_path))
    print(f"[V8A] Reference has {len(reference)} samples")

    # Calculate accuracy metrics
    print("[V8A] Calculating accuracy metrics...")
    accuracy_metrics = calculate_metrics(samples, reference)

    # Calculate resource metrics
    print("[V8A] Calculating resource metrics...")
    resource_metrics = calculate_resource_metrics(samples)

    # Write metrics JSON
    metrics_json = {
        "esp32_replay_status": "PASS" if accuracy_metrics.get("mae", float('inf')) < 0.001 else "WARN",
        "accuracy": accuracy_metrics,
        "resources": resource_metrics,
        "validation_timestamp": "2026-05-16T20:00:00Z",
        "model_version": "v7b_legacy_reconstructed",
        "pipeline": "tflite_micro",
    }

    metrics_out = out_dir / "v8a_esp32_replay_metrics.json"
    with open(metrics_out, 'w') as f:
        json.dump(metrics_json, f, indent=2)
    print(f"[V8A] Wrote metrics: {metrics_out}")

    # Write comparison CSV
    print("[V8A] Writing comparison CSV...")
    comparison_out = out_dir / "v8a_esp32_replay_comparison.csv"
    with open(comparison_out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'sample_id', 'soc_esp32', 'soc_reference_v7b', 'absolute_error', 'percent_error'
        ])
        writer.writeheader()

        for sample in samples:
            sid = sample['sample_id']
            if sid in reference:
                soc_esp32 = sample['soc_esp32']
                soc_ref = reference[sid]
                abs_err = abs(soc_esp32 - soc_ref)
                pct_err = (abs_err / soc_ref * 100) if soc_ref != 0 else 0
                writer.writerow({
                    'sample_id': sid,
                    'soc_esp32': f"{soc_esp32:.6f}",
                    'soc_reference_v7b': f"{soc_ref:.6f}",
                    'absolute_error': f"{abs_err:.6f}",
                    'percent_error': f"{pct_err:.2f}",
                })
    print(f"[V8A] Wrote comparison: {comparison_out}")

    # Write resource CSV
    print("[V8A] Writing resource metrics CSV...")
    resource_out = out_dir / "v8a_esp32_resource_metrics.csv"
    with open(resource_out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'sample_id', 'inference_time_ms', 'free_heap', 'min_free_heap', 'max_alloc_heap'
        ])
        writer.writeheader()

        for sample in samples:
            writer.writerow({
                'sample_id': sample['sample_id'],
                'inference_time_ms': f"{sample['inference_time_ms']:.6f}",
                'free_heap': sample['free_heap'],
                'min_free_heap': sample['min_free_heap'],
                'max_alloc_heap': sample['max_alloc_heap'],
            })
    print(f"[V8A] Wrote resources: {resource_out}")

    print("[V8A] INGESTÃO COMPLETA")
    print(f"  - Amostras: {len(samples)}")
    print(f"  - Pareadas: {accuracy_metrics.get('matched_samples', 0)}")
    print(f"  - MAE: {accuracy_metrics.get('mae', 'N/A'):.6f}")
    print(f"  - RMSE: {accuracy_metrics.get('rmse', 'N/A'):.6f}")
    print(f"  - R²: {accuracy_metrics.get('r2', 'N/A'):.6f}")


if __name__ == '__main__':
    main()
