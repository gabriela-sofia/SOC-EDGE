#!/usr/bin/env python3
"""
Empacotador V8B2 — Monta ZIP de handoff operacional ESP32.

Uso:
  python scripts/package_v8b2_esp32_handoff.py
  python scripts/package_v8b2_esp32_handoff.py --dry-run
"""

import sys
import shutil
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict


class V8B2HandoffPackager:
    """Montador do handoff V8B2 para ESP32."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.root = Path(".")
        self.temp_dir: Path | None = None
        self.files_included = []
        self.warnings = []
        self.errors = []

    def log(self, msg: str, level: str = "INFO"):
        """Log mensagem."""
        prefix = f"[{level}]" if level != "INFO" else ""
        print(f"{prefix} {msg}")

    def warn(self, msg: str):
        """Registra warning."""
        self.log(msg, "WARN")
        self.warnings.append(msg)

    def error(self, msg: str):
        """Registra erro."""
        self.log(msg, "ERROR")
        self.errors.append(msg)

    def check_required_dirs(self) -> bool:
        """Verifica se diretórios críticos existem."""
        required = [
            "embedded/handoff_v8b2/firmware",
            "embedded/handoff_v8b2/include",
            "embedded/handoff_v8b2/replay",
            "embedded/handoff_v8b2/anomaly",
            "embedded/handoff_v8b2/validation",
            "embedded/handoff_v8b2/manifests",
            "embedded/handoff_operator/v8b2_replay_benchmark_handoff",
            "scripts",
        ]

        for dir_path in required:
            if not (self.root / dir_path).exists():
                self.error(f"Diretório obrigatório não encontrado: {dir_path}")
                return False

        return True

    def check_required_files(self) -> bool:
        """Verifica se arquivos críticos existem."""
        required = [
            "embedded/handoff_v8b2/firmware/firmware_soc_v8b2_canonical.ino",
            "embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h",
            "embedded/handoff_v8b2/include/replay_vectors_v8b2.h",
            "embedded/handoff_v8b2/validation/validate_esp32_v8b2.py",
        ]

        for file_path in required:
            if not (self.root / file_path).exists():
                self.error(f"Arquivo obrigatório não encontrado: {file_path}")
                return False

        return True

    def should_exclude(self, path: Path) -> bool:
        """Verifica se um arquivo/pasta deve ser excluído."""
        name = path.name
        parent = path.parent.name

        exclude_patterns = {
            ".git", ".gitignore", ".pytest_cache", "__pycache__",
            "*.pyc", ".DS_Store", "Thumbs.db", "*.tmp", ".env",
        }

        # Excluir pastas específicas
        if name in exclude_patterns or parent in exclude_patterns:
            return True

        # Excluir extensões
        if name.endswith(('.pyc', '.pyo', '.tmp')):
            return True

        # Excluir outputs massivos
        if 'outputs' in str(path):
            return True
        if 'local_runs' in str(path):
            return True

        return False

    def collect_files(self, src_dir: Path) -> List[Path]:
        """Coleta arquivos de um diretório, respeitando exclusões."""
        files = []
        if not src_dir.exists():
            return files

        for item in src_dir.rglob("*"):
            if self.should_exclude(item):
                continue
            if item.is_file():
                files.append(item)

        return files

    def create_package_manifest(self) -> Dict:
        """Cria manifest do pacote."""
        return {
            "package_name": "SOC_EDGE_V8B2_ESP32_HANDOFF",
            "generated_at": datetime.now().isoformat(),
            "source_branch": "repo-scientific-organization",
            "source_commit": self._get_git_commit(),
            "included_sections": [
                "documentation",
                "firmware",
                "model_weights",
                "replay_data",
                "anomaly_scenarios",
                "validation_scripts",
                "reference_results",
                "return_templates",
                "quantization_candidate",
            ],
            "required_return_files": [
                "ambiente_esp32.md",
                "resultados_execucao.md",
                "observacoes_operador.md",
                "v8b2_benchmark_summary.json",
                "v8b2_benchmark_metrics.csv",
                "logs/v8b2_esp32_golden_log.txt",
                "logs/v8b2_esp32_extended_log.txt",
                "logs/v8b2_esp32_anomaly_log.txt",
            ],
            "claim_limits": {
                "replay_embarcado": "permitido",
                "benchmark_latencia_heap": "permitido",
                "campo_producao": "proibido",
                "sensor_fisico_real": "proibido",
                "firmware_int8_validado": "proibido",
                "soh_operacional": "proibido",
                "24_7": "proibido",
            },
            "validation_commands": [
                "python scripts/check_v8b2_package.py",
                "python scripts/package_v8b2_esp32_handoff.py --dry-run",
                "python -m pytest",
            ],
        }

    def _get_git_commit(self) -> str:
        """Tenta obter commit atual."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def copy_section(self, section_name: str, src_patterns: List[str], dest_subdir: str) -> bool:
        """Copia um grupo de arquivos."""
        assert self.temp_dir is not None, "temp_dir deve ser inicializado"

        self.log(f"Copiando {section_name}...")

        dest_dir = self.temp_dir / dest_subdir
        copied_count = 0

        for pattern in src_patterns:
            src_path = self.root / pattern
            if not src_path.exists():
                self.warn(f"Caminho não encontrado: {pattern}")
                continue

            if src_path.is_file():
                dest_file = dest_dir / src_path.name
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                if not self.dry_run:
                    shutil.copy2(src_path, dest_file)
                rel_file = dest_file.relative_to(self.temp_dir)
                self.files_included.append(str(rel_file))
                copied_count += 1

            elif src_path.is_dir():
                files = self.collect_files(src_path)
                for file in files:
                    rel_path = file.relative_to(src_path.parent)
                    dest_file = dest_dir / src_path.name / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    if not self.dry_run:
                        shutil.copy2(file, dest_file)
                    rel_file = dest_file.relative_to(self.temp_dir)
                    self.files_included.append(str(rel_file))
                    copied_count += 1

        self.log(f"  {copied_count} arquivos copiados para {dest_subdir}")
        return copied_count > 0

    def package(self) -> bool:
        """Executa empacotamento completo."""
        self.log("=== Empacotador V8B2 ESP32 ===")

        # Verificações
        if not self.check_required_dirs():
            self.error("Diretórios obrigatórios faltando")
            return False

        if not self.check_required_files():
            self.error("Arquivos obrigatórios faltando")
            return False

        # Criar diretório temporário
        output_dir = self.root / "local_runs" / "handoffs"
        self.temp_dir = output_dir / "SOC_EDGE_V8B2_ESP32_HANDOFF"

        if not self.dry_run:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"Diretório temporário criado: {self.temp_dir}")
        else:
            self.log("[DRY-RUN] Nenhum arquivo será escrito")

        # Copiar seções
        sections = [
            ("Documentação", [
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/README.md",
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/CHECKLIST_EXECUCAO.md",
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/RESULTADOS_ESPERADOS.md",
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/TEMPLATE_RETORNO_OPERADOR.md",
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/MAPA_ARQUIVOS.md",
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/LIMITES_DE_CLAIM.md",
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/TROUBLESHOOTING.md",
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/COMANDOS_VALIDACAO_LOCAL.md",
            ], ""),

            ("Firmware", [
                "embedded/handoff_v8b2/firmware",
            ], "firmware"),

            ("Includes", [
                "embedded/handoff_v8b2/include",
            ], "include"),

            ("Replay", [
                "embedded/handoff_v8b2/replay",
            ], "replay"),

            ("Anomaly", [
                "embedded/handoff_v8b2/anomaly",
            ], "anomaly"),

            ("Validation", [
                "embedded/handoff_v8b2/validation",
            ], "validation"),

            ("Manifests", [
                "embedded/handoff_v8b2/manifests",
            ], "manifests"),

            ("Resultados GOLDEN", [
                "embedded/handoff_v8b2/results_golden",
            ], "results_golden"),

            ("Resultados EXTENDED", [
                "embedded/handoff_v8b2/results_extended",
            ], "results_extended"),

            ("Resultados ANOMALY", [
                "embedded/handoff_v8b2/results_anomaly",
            ], "results_anomaly"),

            ("Template de Resultados", [
                "embedded/handoff_v8b2/results_template",
            ], "results_template"),

            ("Logs de Referência", [
                "embedded/handoff_v8b2/v8b2_esp32_golden_log.txt",
                "embedded/handoff_v8b2/v8b2_esp32_extended_log.txt",
                "embedded/handoff_v8b2/v8b2_esp32_anomaly_log.txt",
            ], ""),

            ("Scripts", [
                "scripts/check_v8b2_package.py",
                "scripts/parse_v8b2_benchmark.py",
                "scripts/analyze_v8b2_model_footprint.py",
                "scripts/compare_v8b2_quantization_schemes.py",
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/scripts",
            ], "scripts"),

            ("Quantização Candidata", [
                "embedded/quantization/README.md",
                "embedded/quantization/V8B2_INT8_CANDIDATE_MANIFEST.json",
                "embedded/quantization/canonical_model_weights_v8b2_int8_candidate.h",
            ], "quantization_candidate"),

            ("Template de Retorno", [
                "embedded/handoff_operator/v8b2_replay_benchmark_handoff/return_package_template",
            ], "return_package_template"),

            ("Arquivos Raiz", [
                "README.md",
                "requirements.txt",
            ], ""),
        ]

        for section_name, patterns, dest_subdir in sections:
            self.copy_section(section_name, patterns, dest_subdir)

        # Gerar manifests
        if not self.dry_run:
            manifest = self.create_package_manifest()
            manifest_file = self.temp_dir / "PACKAGE_MANIFEST.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            self.files_included.append("PACKAGE_MANIFEST.json")
            self.log("Manifest JSON criado")

        # Gerar SHA256SUMS
        if not self.dry_run:
            sha256_file = self.temp_dir / "SHA256SUMS.txt"
            with open(sha256_file, 'w') as f:
                for file_path in sorted(self.files_included):
                    full_path = self.temp_dir / file_path
                    if full_path.is_file():
                        try:
                            hash_val = self._sha256_file(full_path)
                            f.write(f"{hash_val}  {file_path}\n")
                        except Exception as e:
                            self.warn(f"Erro ao hash {file_path}: {e}")
            self.log("SHA256SUMS.txt criado")

        # Criar ZIP
        if self.dry_run:
            self.log(f"[DRY-RUN] Seria criado ZIP em: local_runs/handoffs/SOC_EDGE_V8B2_ESP32_HANDOFF.zip")
            self.log(f"[DRY-RUN] Total de arquivos: {len(self.files_included)}")
            return True

        zip_path = output_dir / "SOC_EDGE_V8B2_ESP32_HANDOFF.zip"
        self.log(f"Criando ZIP: {zip_path}")

        try:
            shutil.make_archive(
                str(zip_path.with_suffix('')),
                'zip',
                self.temp_dir
            )
            self.log(f"ZIP criado com sucesso: {zip_path}")

            # Calcular hash do ZIP
            zip_hash = self._sha256_file(zip_path)
            zip_size = zip_path.stat().st_size / (1024 * 1024)
            self.log(f"Tamanho ZIP: {zip_size:.1f} MB")
            self.log(f"SHA256 ZIP: {zip_hash}")

            return True

        except Exception as e:
            self.error(f"Erro ao criar ZIP: {e}")
            return False

    def _sha256_file(self, filepath: Path) -> str:
        """Calcula SHA256 de um arquivo."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def report(self):
        """Imprime relatório final."""
        print()
        print("=== RELATÓRIO FINAL ===")
        print(f"Total de arquivos inclusos: {len(self.files_included)}")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  - {w}")

        if self.errors:
            print(f"\nErros ({len(self.errors)}):")
            for e in self.errors:
                print(f"  - {e}")

        if not self.errors:
            zip_path = self.root / "local_runs" / "handoffs" / "SOC_EDGE_V8B2_ESP32_HANDOFF.zip"
            if zip_path.exists():
                print(f"\n[OK] ZIP criado: {zip_path}")
            else:
                print("\n[WARN] ZIP nao foi criado (verificar erros acima)")

        return len(self.errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Empacotador V8B2 — Monta ZIP para ESP32"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Listar arquivos sem criar ZIP")

    args = parser.parse_args()

    packager = V8B2HandoffPackager(dry_run=args.dry_run)
    success = packager.package()
    packager.report()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
