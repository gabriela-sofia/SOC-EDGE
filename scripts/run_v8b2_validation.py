from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_VALIDATOR = REPO_ROOT / "embedded" / "handoff_v8b2" / "validation" / "validate_esp32_v8b2.py"


def build_command(log_path: Path, output_dir: Path | None = None) -> list[str]:
    command = [sys.executable, str(CANONICAL_VALIDATOR), str(log_path)]
    if output_dir is not None:
        command.extend(["--output-dir", str(output_dir)])
    return command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the canonical V8B2 ESP32 log validator without duplicating validator logic."
    )
    parser.add_argument("log", type=Path, help="Path to the ESP32 serial log.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional directory for validator outputs.")
    args = parser.parse_args(argv)

    if not CANONICAL_VALIDATOR.is_file():
        print(f"Canonical validator not found: {CANONICAL_VALIDATOR}", file=sys.stderr)
        return 1

    if not args.log.is_file():
        print(f"ESP32 log not found: {args.log}", file=sys.stderr)
        return 1

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(build_command(args.log, args.output_dir), check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
