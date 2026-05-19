from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


FIELDS = [
    "sample_id",
    "mode",
    "soc_final",
    "inference_time_ms",
    "free_heap",
    "min_free_heap",
    "max_alloc_heap",
    "anomaly_flag",
    "anomaly_code",
    "status",
]

VALID_MODES = {"GOLDEN", "EXTENDED", "ANOMALY"}


@dataclass(frozen=True)
class BenchmarkRecord:
    source: str
    line_number: int
    sample_id: int
    mode: str
    soc_final: float
    inference_time_ms: float
    free_heap: int
    min_free_heap: int
    max_alloc_heap: int
    anomaly_flag: int
    anomaly_code: int
    status: str


@dataclass(frozen=True)
class ParseError:
    source: str
    line_number: int
    line: str
    reason: str


def _looks_like_record(line: str) -> bool:
    first = line.split(",", 1)[0].strip()
    return bool(first) and first.lstrip("-").isdigit()


def _parse_record(parts: list[str], source: str, line_number: int) -> BenchmarkRecord:
    if len(parts) != len(FIELDS):
        raise ValueError(f"expected {len(FIELDS)} fields, got {len(parts)}")

    mode = parts[1].strip().upper()
    if mode not in VALID_MODES:
        raise ValueError(f"unexpected mode: {mode}")

    return BenchmarkRecord(
        source=source,
        line_number=line_number,
        sample_id=int(parts[0]),
        mode=mode,
        soc_final=float(parts[2]),
        inference_time_ms=float(parts[3]),
        free_heap=int(parts[4]),
        min_free_heap=int(parts[5]),
        max_alloc_heap=int(parts[6]),
        anomaly_flag=int(parts[7]),
        anomaly_code=int(parts[8]),
        status=parts[9].strip().upper(),
    )


def parse_log_lines(lines: Iterable[str], source: str = "<memory>") -> tuple[list[BenchmarkRecord], list[ParseError]]:
    records: list[BenchmarkRecord] = []
    errors: list[ParseError] = []

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if not _looks_like_record(line):
            continue

        parts = [part.strip() for part in line.split(",")]
        try:
            records.append(_parse_record(parts, source, line_number))
        except (TypeError, ValueError) as exc:
            errors.append(ParseError(source, line_number, line, str(exc)))

    return records, errors


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percent
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _duplicate_count(values: list[int]) -> int:
    return len(values) - len(set(values))


def is_status_ok(status: str) -> bool:
    normalized = status.upper()
    if normalized.startswith(("FAIL", "ERROR")):
        return False
    return normalized.startswith(("PASS", "OK", "WARN", "ANOMALY"))


def compute_mode_metrics(records: list[BenchmarkRecord], parse_errors: list[ParseError] | None = None) -> dict[str, dict[str, object]]:
    parse_errors = parse_errors or []
    metrics: dict[str, dict[str, object]] = {}

    for mode in sorted({record.mode for record in records} | VALID_MODES):
        mode_records = [record for record in records if record.mode == mode]
        mode_errors = [error for error in parse_errors if f",{mode}," in error.line.upper()]
        latencies = [record.inference_time_ms for record in mode_records]
        free_heap = [record.free_heap for record in mode_records]
        min_free_heap = [record.min_free_heap for record in mode_records]
        max_alloc_heap = [record.max_alloc_heap for record in mode_records]
        sample_ids = [record.sample_id for record in mode_records]
        status_ok = sum(1 for record in mode_records if is_status_ok(record.status))
        status_fail = sum(1 for record in mode_records if not is_status_ok(record.status))
        anomaly_count = sum(1 for record in mode_records if record.anomaly_flag != 0)

        metrics[mode] = {
            "n_records": len(mode_records),
            "n_parse_errors": len(mode_errors),
            "n_status_ok": status_ok,
            "n_status_fail": status_fail,
            "anomaly_flag_count": anomaly_count,
            "anomaly_rate": anomaly_count / len(mode_records) if mode_records else None,
            "latency_mean_ms": statistics.fmean(latencies) if latencies else None,
            "latency_median_ms": statistics.median(latencies) if latencies else None,
            "latency_p95_ms": percentile(latencies, 0.95),
            "latency_p99_ms": percentile(latencies, 0.99),
            "latency_max_ms": max(latencies) if latencies else None,
            "free_heap_min_bytes": min(free_heap) if free_heap else None,
            "free_heap_mean_bytes": statistics.fmean(free_heap) if free_heap else None,
            "min_free_heap_min_bytes": min(min_free_heap) if min_free_heap else None,
            "max_alloc_heap_min_bytes": min(max_alloc_heap) if max_alloc_heap else None,
            "sample_id_min": min(sample_ids) if sample_ids else None,
            "sample_id_max": max(sample_ids) if sample_ids else None,
            "sample_id_unique_count": len(set(sample_ids)),
            "duplicate_sample_id_count": _duplicate_count(sample_ids),
        }

    return metrics


def compute_global_metrics(records: list[BenchmarkRecord], parse_errors: list[ParseError]) -> dict[str, object]:
    latencies = [record.inference_time_ms for record in records]
    free_heap = [record.free_heap for record in records]
    status_ok = sum(1 for record in records if is_status_ok(record.status))

    return {
        "total_records": len(records),
        "total_parse_errors": len(parse_errors),
        "modes_seen": sorted({record.mode for record in records}),
        "overall_latency_mean_ms": statistics.fmean(latencies) if latencies else None,
        "overall_latency_p95_ms": percentile(latencies, 0.95),
        "overall_free_heap_min_bytes": min(free_heap) if free_heap else None,
        "overall_status_ok_rate": status_ok / len(records) if records else None,
    }


def load_logs(paths: list[Path]) -> tuple[list[BenchmarkRecord], list[ParseError]]:
    records: list[BenchmarkRecord] = []
    errors: list[ParseError] = []
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            file_records, file_errors = parse_log_lines(handle, str(path))
        records.extend(file_records)
        errors.extend(file_errors)
    return records, errors


def write_json_report(path: Path, global_metrics: dict[str, object], mode_metrics: dict[str, dict[str, object]], parse_errors: list[ParseError]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "global": global_metrics,
        "modes": mode_metrics,
        "parse_errors": [asdict(error) for error in parse_errors],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv_metrics(path: Path, mode_metrics: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["mode"] + sorted(next(iter(mode_metrics.values())).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for mode, metrics in sorted(mode_metrics.items()):
            writer.writerow({"mode": mode, **metrics})


def format_value(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def print_report(global_metrics: dict[str, object], mode_metrics: dict[str, dict[str, object]], parse_errors: list[ParseError]) -> None:
    print("V8B2 embedded benchmark")
    print(f"Total records: {global_metrics['total_records']}")
    print(f"Parse errors: {global_metrics['total_parse_errors']}")
    print(f"Modes seen: {', '.join(global_metrics['modes_seen'])}")
    print(f"Overall latency mean ms: {format_value(global_metrics['overall_latency_mean_ms'])}")
    print(f"Overall latency p95 ms: {format_value(global_metrics['overall_latency_p95_ms'])}")
    print(f"Overall free heap min bytes: {format_value(global_metrics['overall_free_heap_min_bytes'])}")
    print(f"Overall status OK rate: {format_value(global_metrics['overall_status_ok_rate'])}")
    print("")
    print("Mode metrics:")
    for mode, metrics in sorted(mode_metrics.items()):
        print(
            f"- {mode}: n={metrics['n_records']}, "
            f"lat_mean_ms={format_value(metrics['latency_mean_ms'])}, "
            f"lat_p95_ms={format_value(metrics['latency_p95_ms'])}, "
            f"heap_min={format_value(metrics['free_heap_min_bytes'])}, "
            f"status_ok={metrics['n_status_ok']}, "
            f"status_fail={metrics['n_status_fail']}, "
            f"anomaly_rate={format_value(metrics['anomaly_rate'])}, "
            f"duplicate_sample_ids={metrics['duplicate_sample_id_count']}"
        )
    if parse_errors:
        print("")
        print("Parse errors:")
        for error in parse_errors[:10]:
            print(f"- {error.source}:{error.line_number}: {error.reason}")
        if len(parse_errors) > 10:
            print(f"- ... {len(parse_errors) - 10} additional parse errors")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse V8B2 ESP32 replay logs and summarize runtime benchmark metrics."
    )
    parser.add_argument("logs", nargs="+", type=Path, help="ESP32 log files to parse.")
    parser.add_argument("--output-dir", type=Path, help="Optional directory for benchmark outputs.")
    parser.add_argument("--json", dest="json_path", type=Path, help="Optional JSON report path.")
    parser.add_argument("--csv", dest="csv_path", type=Path, help="Optional CSV mode metrics path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for log_path in args.logs:
        if not log_path.exists():
            print(f"Missing log file: {log_path}", file=sys.stderr)
            return 1

    records, parse_errors = load_logs(args.logs)
    if not records:
        print("No valid V8B2 benchmark records found.", file=sys.stderr)
        return 1

    global_metrics = compute_global_metrics(records, parse_errors)
    mode_metrics = compute_mode_metrics(records, parse_errors)
    print_report(global_metrics, mode_metrics, parse_errors)

    output_dir = args.output_dir
    json_path = args.json_path
    csv_path = args.csv_path
    if output_dir:
        json_path = json_path or output_dir / "v8b2_benchmark_summary.json"
        csv_path = csv_path or output_dir / "v8b2_benchmark_metrics.csv"
    if json_path:
        write_json_report(json_path, global_metrics, mode_metrics, parse_errors)
    if csv_path:
        write_csv_metrics(csv_path, mode_metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
