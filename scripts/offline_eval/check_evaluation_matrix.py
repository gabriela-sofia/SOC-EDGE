from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MATRIX = Path("experiments/registries/evaluation_matrix.csv")
REQUIRED_COLUMNS = [
    "evaluation_id",
    "objeto_avaliado",
    "split",
    "metrica",
    "objetivo",
    "threshold_inicial",
    "obrigatoria_para_claim",
    "observacoes",
]
OFFLINE_METRICS = {"MAE", "RMSE", "R2", "max_abs_error", "p95_abs_error"}
EMBEDDED_METRICS = {"latency_mean_ms", "latency_p95_ms", "heap_min_bytes", "sample_id_match_rate"}
ANOMALY_METRICS = {"anomaly_recall", "anomaly_false_positive_rate"}
REQUIRED_SPLIT_PATTERNS = ["temporal", "ciclo", "célula", "leave-one-cell-out", "replay embarcado"]


@dataclass(frozen=True)
class CheckMessage:
    level: str
    item: str
    message: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_matrix(rows: list[dict[str, str]]) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    if not rows:
        return [CheckMessage("FAIL", "matrix", "Evaluation matrix is empty.")]

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in rows[0]]
    if missing_columns:
        messages.append(CheckMessage("FAIL", "columns", "Missing columns: " + ", ".join(missing_columns)))
        return messages
    messages.append(CheckMessage("PASS", "columns", "Required columns are present."))

    ids = [row["evaluation_id"] for row in rows]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        messages.append(CheckMessage("FAIL", "evaluation_id", "Duplicate IDs: " + ", ".join(duplicates)))
    else:
        messages.append(CheckMessage("PASS", "evaluation_id", "IDs are unique."))

    for index, row in enumerate(rows, start=2):
        for column in REQUIRED_COLUMNS:
            if not row.get(column, "").strip():
                messages.append(CheckMessage("FAIL", f"line {index}", f"Required field is empty: {column}"))

    metrics = {row["metrica"] for row in rows}
    for label, required in (
        ("offline metrics", OFFLINE_METRICS),
        ("embedded metrics", EMBEDDED_METRICS),
        ("anomaly metrics", ANOMALY_METRICS),
    ):
        missing = sorted(required - metrics)
        if missing:
            messages.append(CheckMessage("FAIL", label, "Missing metrics: " + ", ".join(missing)))
        else:
            messages.append(CheckMessage("PASS", label, "Required metrics are present."))

    split_text = " | ".join(row["split"] for row in rows).lower()
    missing_splits = [pattern for pattern in REQUIRED_SPLIT_PATTERNS if pattern.lower() not in split_text]
    if missing_splits:
        messages.append(CheckMessage("FAIL", "splits", "Missing split patterns: " + ", ".join(missing_splits)))
    else:
        messages.append(CheckMessage("PASS", "splits", "Required split patterns are present."))

    if not any(message.level == "FAIL" for message in messages):
        messages.append(CheckMessage("PASS", "matrix", "Evaluation matrix is structurally valid."))
    return messages


def print_messages(messages: list[CheckMessage]) -> str:
    status = "FAIL" if any(message.level == "FAIL" for message in messages) else "PASS"
    print(f"Evaluation matrix audit: {status}")
    for message in messages:
        print(f"[{message.level}] {message.item}: {message.message}")
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit SOC-EDGE evaluation matrix.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = read_csv(args.matrix)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    status = print_messages(validate_matrix(rows))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
