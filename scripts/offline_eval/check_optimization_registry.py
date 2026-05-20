from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_REGISTRY = Path("experiments/registries/optimization_registry.csv")
DEFAULT_SCHEMA = Path("experiments/schemas/optimization_registry_schema.csv")
REQUIRED_FRONTS = {
    "target físico",
    "features",
    "splits",
    "modelos",
    "híbridos",
    "quantização",
    "anomalias",
    "drift",
    "SOH",
    "embarcado",
}


@dataclass(frozen=True)
class CheckMessage:
    level: str
    item: str
    message: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def schema_fields(schema_rows: list[dict[str, str]]) -> tuple[list[str], dict[str, set[str]]]:
    required = [row["field"] for row in schema_rows if row.get("required", "").lower() == "true"]
    allowed = {}
    for row in schema_rows:
        values = row.get("allowed_values", "").strip()
        if values:
            allowed[row["field"]] = {value.strip() for value in values.split("|")}
    return required, allowed


def validate_registry(registry_rows: list[dict[str, str]], schema_rows: list[dict[str, str]]) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    required_fields, allowed_values = schema_fields(schema_rows)
    if not registry_rows:
        return [CheckMessage("FAIL", "registry", "Registry is empty.")]

    fieldnames = set(registry_rows[0].keys())
    missing_columns = [field for field in required_fields if field not in fieldnames]
    if missing_columns:
        messages.append(CheckMessage("FAIL", "columns", "Missing columns: " + ", ".join(missing_columns)))
        return messages
    messages.append(CheckMessage("PASS", "columns", "Required columns are present."))

    ids = [row["optimization_id"] for row in registry_rows]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        messages.append(CheckMessage("FAIL", "optimization_id", "Duplicate IDs: " + ", ".join(duplicates)))
    else:
        messages.append(CheckMessage("PASS", "optimization_id", "IDs are unique."))

    for index, row in enumerate(registry_rows, start=2):
        for field in required_fields:
            if not row.get(field, "").strip():
                messages.append(CheckMessage("FAIL", f"line {index}", f"Required field is empty: {field}"))
        for field, allowed in allowed_values.items():
            value = row.get(field, "").strip()
            if value and value not in allowed:
                messages.append(CheckMessage("FAIL", f"line {index}", f"Invalid value for {field}: {value}"))
        if not row.get("claim_permitido", "").strip() or not row.get("claim_proibido", "").strip():
            messages.append(CheckMessage("FAIL", f"line {index}", "Claims must be explicit."))

    fronts = {row["frente"] for row in registry_rows}
    missing_fronts = sorted(REQUIRED_FRONTS - fronts)
    if missing_fronts:
        messages.append(CheckMessage("FAIL", "frentes", "Missing fronts: " + ", ".join(missing_fronts)))
    else:
        messages.append(CheckMessage("PASS", "frentes", "All required fronts are represented."))

    if not any(message.level == "FAIL" for message in messages):
        messages.append(CheckMessage("PASS", "registry", "Optimization registry is structurally valid."))
    return messages


def print_messages(messages: list[CheckMessage]) -> str:
    status = "FAIL" if any(message.level == "FAIL" for message in messages) else "PASS"
    print(f"Optimization registry audit: {status}")
    for message in messages:
        print(f"[{message.level}] {message.item}: {message.message}")
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit SOC-EDGE optimization registry.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry_rows = read_csv(args.registry)
        schema_rows = read_csv(args.schema)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    status = print_messages(validate_registry(registry_rows, schema_rows))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
