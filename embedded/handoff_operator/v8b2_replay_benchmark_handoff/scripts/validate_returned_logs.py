#!/usr/bin/env python3
"""
Validador V8B2 — Processa logs de ESP32 e retorna métricas.

Uso:
  python validate_returned_logs.py --golden golden.txt --extended extended.txt --anomaly anomaly.txt
  python validate_returned_logs.py --golden golden.txt --json out.json --csv out.csv
"""

import sys
import csv
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class V8B2LogValidator:
    """Validador de logs V8B2."""

    EXPECTED_FIELDS = [
        "sample_id", "mode", "soc_final", "inference_time_ms",
        "free_heap", "min_free_heap", "max_alloc_heap",
        "anomaly_flag", "anomaly_code", "status"
    ]
    EXPECTED_MODES = {"GOLDEN", "EXTENDED", "ANOMALY"}
    EXPECTED_STATUS = {"OK", "FAIL"}

    def __init__(self):
        self.records = []
        self.errors = []
        self.mode_stats = {}

    def load_log(self, filepath: str) -> bool:
        """Carrega e parseia um log."""
        if not Path(filepath).exists():
            self.errors.append(f"Arquivo não existe: {filepath}")
            return False

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    self.errors.append(f"Log vazio: {filepath}")
                    return False

                for i, row in enumerate(reader, start=2):  # start=2 pq header é linha 1
                    record, error = self._parse_row(row, filepath, i)
                    if error:
                        self.errors.append(error)
                    else:
                        self.records.append(record)

            return len(self.errors) == 0 or len(self.records) > 0
        except Exception as e:
            self.errors.append(f"Erro ao ler {filepath}: {e}")
            return False

    def _parse_row(self, row: Dict, filepath: str, line_num: int) -> Tuple[Optional[Dict], Optional[str]]:
        """Parseia uma linha do log."""
        try:
            # Validar campos
            if not all(field in row for field in self.EXPECTED_FIELDS):
                missing = [f for f in self.EXPECTED_FIELDS if f not in row]
                return None, f"{filepath}:{line_num} - Campos faltando: {missing}"

            # Converter tipos
            sample_id = int(row["sample_id"])
            mode = row["mode"].strip()
            soc_final = float(row["soc_final"])
            inference_time_ms = float(row["inference_time_ms"])
            free_heap = int(row["free_heap"])
            min_free_heap = int(row["min_free_heap"]) if row["min_free_heap"].strip() else 0
            max_alloc_heap = int(row["max_alloc_heap"]) if row["max_alloc_heap"].strip() else 0
            anomaly_flag = int(row["anomaly_flag"]) if row["anomaly_flag"].strip() else 0
            anomaly_code = int(row["anomaly_code"]) if row["anomaly_code"].strip() else 0
            status = row["status"].strip()

            # Validar valores
            if mode not in self.EXPECTED_MODES:
                return None, f"{filepath}:{line_num} - Modo inválido: {mode}"

            if status not in self.EXPECTED_STATUS:
                return None, f"{filepath}:{line_num} - Status inválido: {status}"

            if inference_time_ms < 0 or free_heap < 0:
                return None, f"{filepath}:{line_num} - Valores negativos inválidos"

            record = {
                "sample_id": sample_id,
                "mode": mode,
                "soc_final": soc_final,
                "inference_time_ms": inference_time_ms,
                "free_heap": free_heap,
                "min_free_heap": min_free_heap,
                "max_alloc_heap": max_alloc_heap,
                "anomaly_flag": anomaly_flag,
                "anomaly_code": anomaly_code,
                "status": status,
            }
            return record, None

        except (ValueError, TypeError) as e:
            return None, f"{filepath}:{line_num} - Erro de parsing: {e}"

    def compute_metrics(self) -> Dict:
        """Computa métricas agregadas e por modo."""
        metrics = {
            "total_records": len(self.records),
            "parse_errors": len(self.errors),
            "status_ok_rate": 0.0,
            "latency_mean_ms": 0.0,
            "latency_p95_ms": 0.0,
            "latency_p99_ms": 0.0,
            "latency_max_ms": 0.0,
            "free_heap_min_bytes": 0,
            "min_free_heap_min_bytes": None,
            "max_alloc_heap_min_bytes": None,
            "anomaly_rate": 0.0,
            "duplicate_sample_id_count": 0,
            "resets_observados": 0,
            "modo_breakdown": {}
        }

        if not self.records:
            return metrics

        # Agregados globais
        ok_count = sum(1 for r in self.records if r["status"] == "OK")
        metrics["status_ok_rate"] = ok_count / len(self.records) if self.records else 0.0

        latencies = [r["inference_time_ms"] for r in self.records]
        latencies.sort()
        metrics["latency_mean_ms"] = sum(latencies) / len(latencies)
        metrics["latency_p95_ms"] = latencies[int(len(latencies) * 0.95)] if latencies else 0
        metrics["latency_p99_ms"] = latencies[int(len(latencies) * 0.99)] if latencies else 0
        metrics["latency_max_ms"] = max(latencies) if latencies else 0

        heaps = [r["free_heap"] for r in self.records]
        metrics["free_heap_min_bytes"] = min(heaps) if heaps else 0

        anomaly_count = sum(1 for r in self.records if r["anomaly_flag"] > 0)
        metrics["anomaly_rate"] = anomaly_count / len(self.records) if self.records else 0.0

        # Duplicate sample_id
        sample_ids = [r["sample_id"] for r in self.records]
        metrics["duplicate_sample_id_count"] = len(sample_ids) - len(set(sample_ids))

        # Por modo
        for mode in self.EXPECTED_MODES:
            mode_records = [r for r in self.records if r["mode"] == mode]
            if mode_records:
                mode_ok = sum(1 for r in mode_records if r["status"] == "OK")
                mode_latencies = [r["inference_time_ms"] for r in mode_records]
                mode_latencies.sort()
                mode_heaps = [r["free_heap"] for r in mode_records]
                mode_anomalies = sum(1 for r in mode_records if r["anomaly_flag"] > 0)

                metrics["modo_breakdown"][mode] = {
                    "n": len(mode_records),
                    "lat_mean_ms": sum(mode_latencies) / len(mode_latencies),
                    "lat_p95_ms": mode_latencies[int(len(mode_latencies) * 0.95)],
                    "heap_min": min(mode_heaps),
                    "status_ok": mode_ok,
                    "status_fail": len(mode_records) - mode_ok,
                    "anomaly_rate": mode_anomalies / len(mode_records) if mode_records else 0.0
                }

        return metrics

    def get_status(self, metrics: Dict) -> str:
        """Determina status geral."""
        if metrics["parse_errors"] > 0:
            return "FAIL"
        if metrics["status_ok_rate"] < 1.0:
            return "FAIL"
        if metrics["free_heap_min_bytes"] < 50000:
            return "WARN"
        return "PASS"

    def report(self, metrics: Dict, output_json: Optional[str] = None, output_csv: Optional[str] = None):
        """Imprime e salva relatório."""
        status = self.get_status(metrics)

        # Console output
        print("V8B2 validation")
        print(f"Total records: {metrics['total_records']}")
        print(f"Parse errors: {metrics['parse_errors']}")
        print(f"Status: {status}")
        print()

        if metrics["total_records"] > 0:
            print(f"Overall latency mean ms: {metrics['latency_mean_ms']:.6f}")
            print(f"Overall latency p95 ms: {metrics['latency_p95_ms']:.6f}")
            print(f"Overall latency max ms: {metrics['latency_max_ms']:.6f}")
            print(f"Overall free heap min bytes: {metrics['free_heap_min_bytes']}")
            print(f"Overall status OK rate: {metrics['status_ok_rate']:.6f}")
            print()

            if metrics["modo_breakdown"]:
                print("Mode metrics:")
                for mode, stats in metrics["modo_breakdown"].items():
                    print(f"- {mode}: n={stats['n']}, lat_mean_ms={stats['lat_mean_ms']:.6f}, "
                          f"lat_p95_ms={stats['lat_p95_ms']:.6f}, heap_min={stats['heap_min']}, "
                          f"status_ok={stats['status_ok']}, status_fail={stats['status_fail']}, "
                          f"anomaly_rate={stats['anomaly_rate']:.6f}, duplicate_sample_ids={metrics['duplicate_sample_id_count']}")

        # JSON output
        if output_json:
            try:
                with open(output_json, 'w') as f:
                    json.dump(metrics, f, indent=2)
                print(f"\nJSON report: {output_json}")
            except Exception as e:
                print(f"Erro ao salvar JSON: {e}", file=sys.stderr)

        # CSV output
        if output_csv:
            try:
                with open(output_csv, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=list(metrics.keys()))
                    writer.writeheader()
                    # Flatten metrics para CSV
                    flat = {k: str(v) if not isinstance(v, dict) else json.dumps(v)
                            for k, v in metrics.items()}
                    writer.writerow(flat)
                print(f"CSV report: {output_csv}")
            except Exception as e:
                print(f"Erro ao salvar CSV: {e}", file=sys.stderr)

        return 0 if status in ["PASS", "WARN"] else 1


def main():
    parser = argparse.ArgumentParser(
        description="Validador V8B2 — Processa logs e retorna métricas."
    )
    parser.add_argument("--golden", help="Path para log GOLDEN")
    parser.add_argument("--extended", help="Path para log EXTENDED")
    parser.add_argument("--anomaly", help="Path para log ANOMALY")
    parser.add_argument("--json", help="Path para saída JSON")
    parser.add_argument("--csv", help="Path para saída CSV")

    args = parser.parse_args()

    if not any([args.golden, args.extended, args.anomaly]):
        parser.print_help()
        return 1

    validator = V8B2LogValidator()

    # Carrega logs
    if args.golden:
        validator.load_log(args.golden)
    if args.extended:
        validator.load_log(args.extended)
    if args.anomaly:
        validator.load_log(args.anomaly)

    # Computa e reporta
    metrics = validator.compute_metrics()
    return validator.report(metrics, args.json, args.csv)


if __name__ == "__main__":
    sys.exit(main())
