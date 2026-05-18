from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


IGNORE_DIRS = {
    "venv", "env", "__pycache__", "node_modules",
}

IGNORE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".bak", ".swp", ".DS_Store"}

TEXT_SUFFIXES = {
    ".py", ".ipynb", ".md", ".txt", ".csv", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".ps1", ".bat", ".sh", ".cpp", ".h",
    ".hpp", ".ino", ".c",
}

HEAVY_SUFFIXES = {
    ".zip", ".rar", ".7z", ".tar", ".gz", ".npy", ".npz", ".pkl",
    ".joblib", ".tflite", ".onnx", ".h5", ".pth", ".pt",
    ".parquet", ".feather", ".xlsx", ".xls",
}


@dataclass
class FileRecord:
    root_name: str
    rel_path: str
    abs_path: str
    suffix: str
    size_bytes: int
    sha256: str | None
    is_text_candidate: bool
    is_heavy_candidate: bool


@dataclass
class ReferenceHit:
    file: str
    line: int
    pattern: str
    text: str


@dataclass
class ImportFinding:
    file: str
    import_name: str
    status: str
    note: str


def is_ignored(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts

    if any(part in IGNORE_DIRS or part.startswith(".") for part in rel_parts):
        return True

    if path.is_file() and path.suffix in IGNORE_SUFFIXES:
        return True

    return False


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)

        dirnames[:] = [
            d for d in dirnames
            if not is_ignored(current / d, root)
        ]

        for name in filenames:
            path = current / name
            if not is_ignored(path, root):
                yield path


def sha256_file(path: Path, max_hash_size_mb: int) -> str | None:
    size_mb = path.stat().st_size / (1024 * 1024)

    if size_mb > max_hash_size_mb:
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def inventory(root: Path, root_name: str, max_hash_size_mb: int) -> list[FileRecord]:
    rows = []

    for path in iter_files(root):
        suffix = path.suffix.lower()
        stat = path.stat()

        rows.append(
            FileRecord(
                root_name=root_name,
                rel_path=str(path.relative_to(root)).replace("\\", "/"),
                abs_path=str(path),
                suffix=suffix,
                size_bytes=stat.st_size,
                sha256=sha256_file(path, max_hash_size_mb),
                is_text_candidate=suffix in TEXT_SUFFIXES,
                is_heavy_candidate=suffix in HEAVY_SUFFIXES,
            )
        )

    return sorted(rows, key=lambda r: r.rel_path.lower())


def read_text_safely(path: Path, max_mb: int = 8) -> str | None:
    try:
        if path.stat().st_size > max_mb * 1024 * 1024:
            return None

        return path.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="latin-1")
        except Exception:
            return None

    except Exception:
        return None


def scan_references(project_root: Path, original_root: Path) -> list[ReferenceHit]:
    original_name = original_root.name

    patterns = {
        "absolute_original_path": re.escape(str(original_root)),
        "windows_original_folder_name": rf"(?i)(^|[^A-Za-z0-9_]){re.escape(original_name)}([^A-Za-z0-9_]|$)",
        "legacy_soc_token": r"(?i)\bSOC\b",
        "handoff_reference": r"(?i)\bhandoff\b",
        "method_b_reference": r"(?i)\bmethod[\s_-]*b\b",
        "esp32_reference": r"(?i)\bESP32\b|\btflite\b|\btensorflow\s*lite\b",
        "dataset_reference": r"(?i)\bOxford\b|\bLG18650\b|\bHG2\b|\bSP2\b|\bIoT\b",
        "artifact_reference": r"(?i)\bscaler\b|\bmodel\b|\bvalidation_package\b|\bfirmware\b|\bparity\b|\breplay\b",
        "path_literal": r"""(?i)([A-Z]:\\|/mnt/|/home/|\.{1,2}/|\.{1,2}\\)[^"'`\s]+""",
    }

    hits = []

    for path in iter_files(project_root):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        text = read_text_safely(path)

        if text is None:
            continue

        rel = str(path.relative_to(project_root)).replace("\\", "/")

        for line_no, line in enumerate(text.splitlines(), start=1):
            for name, pattern in patterns.items():
                if re.search(pattern, line):
                    clean = line.strip()

                    if len(clean) > 260:
                        clean = clean[:257] + "..."

                    hits.append(
                        ReferenceHit(
                            file=rel,
                            line=line_no,
                            pattern=name,
                            text=clean,
                        )
                    )

    return hits


def python_module_names(root: Path) -> set[str]:
    names = set()

    for path in iter_files(root):
        if path.suffix.lower() != ".py":
            continue

        rel = path.relative_to(root)
        parts = list(rel.parts)

        if parts[-1] == "__init__.py":
            module_parts = parts[:-1]
        else:
            module_parts = parts[:-1] + [path.stem]

        if module_parts:
            names.add(".".join(module_parts))
            names.add(module_parts[0])

    return names


def extract_import_roots(py_file: Path) -> set[str]:
    text = read_text_safely(py_file)

    if text is None:
        return set()

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    return imports


def scan_imports(project_root: Path, original_root: Path) -> list[ImportFinding]:
    project_modules = python_module_names(project_root)
    original_modules = python_module_names(original_root)

    stdlib_or_external_likely = {
        "os", "sys", "json", "csv", "math", "time", "datetime", "pathlib",
        "typing", "dataclasses", "argparse", "re", "hashlib", "statistics",
        "collections", "itertools", "functools", "subprocess", "shutil",
        "numpy", "pandas", "sklearn", "tensorflow", "torch", "matplotlib",
        "scipy", "joblib", "serial",
    }

    findings = []

    for path in iter_files(project_root):
        if path.suffix.lower() != ".py":
            continue

        rel = str(path.relative_to(project_root)).replace("\\", "/")

        for imp in sorted(extract_import_roots(path)):
            if imp in stdlib_or_external_likely:
                continue

            in_project = imp in project_modules
            in_original = imp in original_modules

            if in_project:
                status = "OK_IN_SOC_PROJECT"
                note = "import resolvido dentro da SOC_PROJECT"
            elif in_original:
                status = "POSSIBLE_LEGACY_DEPENDENCY"
                note = "modulo nao encontrado na SOC_PROJECT, mas existe na SOC original"
            else:
                status = "UNRESOLVED_OR_EXTERNAL"
                note = "nao encontrado como modulo local em nenhuma das duas pastas"

            findings.append(
                ImportFinding(
                    file=rel,
                    import_name=imp,
                    status=status,
                    note=note,
                )
            )

    return findings


def compare_inventories(original: list[FileRecord], project: list[FileRecord]) -> dict[str, list[dict]]:
    original_by_rel = {r.rel_path: r for r in original}
    project_by_rel = {r.rel_path: r for r in project}

    only_original = []
    only_project = []
    same_rel_same_hash = []
    same_rel_different_hash = []
    same_hash_different_path = []

    for rel, row in original_by_rel.items():
        if rel not in project_by_rel:
            only_original.append(asdict(row))
        else:
            other = project_by_rel[rel]

            if row.sha256 and other.sha256 and row.sha256 == other.sha256:
                same_rel_same_hash.append(
                    {
                        "rel_path": rel,
                        "sha256": row.sha256,
                        "size_bytes": row.size_bytes,
                    }
                )
            else:
                same_rel_different_hash.append(
                    {
                        "rel_path": rel,
                        "original_size": row.size_bytes,
                        "project_size": other.size_bytes,
                        "original_sha256": row.sha256,
                        "project_sha256": other.sha256,
                    }
                )

    for rel, row in project_by_rel.items():
        if rel not in original_by_rel:
            only_project.append(asdict(row))

    original_hashes = {}

    for r in original:
        if r.sha256:
            original_hashes.setdefault(r.sha256, []).append(r)

    for p in project:
        if not p.sha256:
            continue

        for o in original_hashes.get(p.sha256, []):
            if o.rel_path != p.rel_path:
                same_hash_different_path.append(
                    {
                        "sha256": p.sha256,
                        "original_rel_path": o.rel_path,
                        "project_rel_path": p.rel_path,
                        "size_bytes": p.size_bytes,
                    }
                )

    return {
        "only_in_original_SOC": only_original,
        "only_in_SOC_PROJECT": only_project,
        "same_relative_path_same_hash": same_rel_same_hash,
        "same_relative_path_different_hash": same_rel_different_hash,
        "same_hash_different_path": same_hash_different_path,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = sorted({k for row in rows for k in row.keys()})

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_summary(
    out_dir: Path,
    original_root: Path,
    project_root: Path,
    original: list[FileRecord],
    project: list[FileRecord],
    comparison: dict[str, list[dict]],
    refs: list[ReferenceHit],
    imports: list[ImportFinding],
) -> None:
    heavy_original = [r for r in original if r.is_heavy_candidate]
    heavy_project = [r for r in project if r.is_heavy_candidate]
    legacy_imports = [i for i in imports if i.status == "POSSIBLE_LEGACY_DEPENDENCY"]

    lines = [
        "# SOC repository bootstrap audit",
        "",
        "Auditoria read-only para decidir o que deve entrar no repositorio publico/versionavel do projeto SOC.",
        "",
        "## Escopo",
        "",
        f"- Pasta original: `{original_root}`",
        f"- Base evoluida do projeto: `{project_root}`",
        "- Nenhum arquivo foi movido, apagado ou copiado.",
        "",
        "## Contagem geral",
        "",
        f"- Arquivos na SOC original: `{len(original)}`",
        f"- Arquivos na SOC_PROJECT: `{len(project)}`",
        f"- Arquivos somente na SOC original: `{len(comparison['only_in_original_SOC'])}`",
        f"- Arquivos somente na SOC_PROJECT: `{len(comparison['only_in_SOC_PROJECT'])}`",
        f"- Mesmo caminho relativo e mesmo hash: `{len(comparison['same_relative_path_same_hash'])}`",
        f"- Mesmo caminho relativo, mas conteudo diferente: `{len(comparison['same_relative_path_different_hash'])}`",
        f"- Mesmo hash em caminhos diferentes: `{len(comparison['same_hash_different_path'])}`",
        "",
        "## Sinais de dependencia legada",
        "",
        f"- Referencias textuais encontradas na SOC_PROJECT: `{len(refs)}`",
        f"- Imports possivelmente dependentes da SOC original: `{len(legacy_imports)}`",
        "",
        "## Artefatos pesados detectados",
        "",
        f"- Artefatos pesados na SOC original: `{len(heavy_original)}`",
        f"- Artefatos pesados na SOC_PROJECT: `{len(heavy_project)}`",
        "",
        "Regra recomendada: artefatos pesados nao devem entrar direto no repositorio. Devem ser representados por manifests, schemas, checksums, summaries e instrucoes de reproducao.",
        "",
        "## Primeiros candidatos a revisao manual: arquivos so na SOC original",
        "",
    ]

    for row in comparison["only_in_original_SOC"][:60]:
        lines.append(f"- `{row['rel_path']}` — {row['size_bytes']} bytes — suffix `{row['suffix']}`")

    if not comparison["only_in_original_SOC"]:
        lines.append("- Nenhum.")

    lines.extend(["", "## Arquivos com mesmo caminho relativo, mas conteudo diferente", ""])

    for row in comparison["same_relative_path_different_hash"][:60]:
        lines.append(f"- `{row['rel_path']}` — original {row['original_size']} bytes / project {row['project_size']} bytes")

    if not comparison["same_relative_path_different_hash"]:
        lines.append("- Nenhum.")

    lines.extend(
        [
            "",
            "## Proxima decisao metodologica",
            "",
            "Depois desta auditoria, a decisao correta nao e copiar a SOC original inteira.",
            "A decisao correta e promover seletivamente para a SOC_PROJECT apenas:",
            "",
            "1. codigo executavel ainda usado;",
            "2. notebooks ou scripts que expliquem a metodologia Method B;",
            "3. schemas de datasets;",
            "4. manifests de validacao;",
            "5. reports cientificos consolidados;",
            "6. firmware/export package realmente usado no V8B2;",
            "7. documentacao de protocolo, validacao embarcada, replay, paridade e criterios de aceite.",
            "",
            "Dados brutos, zips, modelos pesados, outputs locais e logs longos devem ficar fora do Git, com rastreabilidade via manifests/checksums.",
            "",
        ]
    )

    (out_dir / "AUDIT_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True)
    parser.add_argument("--project", default=".")
    parser.add_argument("--out", default="audit_reports/repo_bootstrap_audit")
    parser.add_argument("--max-hash-size-mb", type=int, default=64)
    args = parser.parse_args()

    original_root = Path(args.original).resolve()
    project_root = Path(args.project).resolve()
    out_dir = Path(args.out).resolve()

    if not original_root.exists():
        raise SystemExit(f"Original folder does not exist: {original_root}")

    if not project_root.exists():
        raise SystemExit(f"Project folder does not exist: {project_root}")

    out_dir.mkdir(parents=True, exist_ok=True)

    original = inventory(original_root, "SOC", args.max_hash_size_mb)
    project = inventory(project_root, "SOC_PROJECT", args.max_hash_size_mb)

    comparison = compare_inventories(original, project)
    refs = scan_references(project_root, original_root)
    imports = scan_imports(project_root, original_root)

    write_csv(out_dir / "inventory_original_SOC.csv", [asdict(r) for r in original])
    write_csv(out_dir / "inventory_SOC_PROJECT.csv", [asdict(r) for r in project])

    for name, rows in comparison.items():
        write_csv(out_dir / f"{name}.csv", rows)

    write_csv(out_dir / "references_to_legacy_or_external_paths.csv", [asdict(r) for r in refs])
    write_csv(out_dir / "python_import_audit.csv", [asdict(i) for i in imports])

    summary = {
        "original_root": str(original_root),
        "project_root": str(project_root),
        "out_dir": str(out_dir),
        "counts": {
            "original_files": len(original),
            "project_files": len(project),
            "only_in_original_SOC": len(comparison["only_in_original_SOC"]),
            "only_in_SOC_PROJECT": len(comparison["only_in_SOC_PROJECT"]),
            "same_relative_path_same_hash": len(comparison["same_relative_path_same_hash"]),
            "same_relative_path_different_hash": len(comparison["same_relative_path_different_hash"]),
            "same_hash_different_path": len(comparison["same_hash_different_path"]),
            "reference_hits": len(refs),
            "possible_legacy_imports": len([i for i in imports if i.status == "POSSIBLE_LEGACY_DEPENDENCY"]),
        },
    }

    (out_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    write_markdown_summary(
        out_dir=out_dir,
        original_root=original_root,
        project_root=project_root,
        original=original,
        project=project,
        comparison=comparison,
        refs=refs,
        imports=imports,
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("")
    print(f"Audit written to: {out_dir}")
    print(f"Open: {out_dir / 'AUDIT_SUMMARY.md'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
