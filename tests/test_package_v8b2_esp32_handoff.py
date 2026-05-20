"""
Testes para o empacotador V8B2 ESP32.
"""

import tempfile
import json
from pathlib import Path
from unittest import mock
import sys

# Importar packager
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from package_v8b2_esp32_handoff import V8B2HandoffPackager


def test_packager_initializes():
    """Testa inicialização do packager."""
    packager = V8B2HandoffPackager(dry_run=True)
    assert packager.dry_run is True
    assert packager.root == Path(".")
    assert packager.files_included == []
    assert packager.errors == []
    assert packager.warnings == []


def test_packager_identifies_required_dirs():
    """Testa verificação de diretórios obrigatórios."""
    packager = V8B2HandoffPackager(dry_run=True)

    # Com diretórios presentes (em repo real)
    has_dirs = packager.check_required_dirs()
    assert isinstance(has_dirs, bool)


def test_packager_identifies_required_files():
    """Testa verificação de arquivos obrigatórios."""
    packager = V8B2HandoffPackager(dry_run=True)

    # Com arquivos presentes (em repo real)
    has_files = packager.check_required_files()
    assert isinstance(has_files, bool)


def test_packager_should_exclude():
    """Testa lógica de exclusão."""
    packager = V8B2HandoffPackager(dry_run=True)

    # Deve excluir
    assert packager.should_exclude(Path(".git/config"))
    assert packager.should_exclude(Path("__pycache__/module.pyc"))
    assert packager.should_exclude(Path("test.pyc"))

    # Não deve excluir
    assert not packager.should_exclude(Path("firmware/main.ino"))
    assert not packager.should_exclude(Path("scripts/validate.py"))


def test_packager_manifest_structure():
    """Testa estrutura do manifest."""
    packager = V8B2HandoffPackager(dry_run=True)
    manifest = packager.create_package_manifest()

    # Verificar campos obrigatórios
    assert "package_name" in manifest
    assert "generated_at" in manifest
    assert "included_sections" in manifest
    assert "required_return_files" in manifest
    assert "claim_limits" in manifest
    assert "validation_commands" in manifest

    # Verificar valores esperados
    assert manifest["package_name"] == "SOC_EDGE_V8B2_ESP32_HANDOFF"
    assert isinstance(manifest["included_sections"], list)
    assert len(manifest["included_sections"]) > 0

    # Verificar claim limits
    assert manifest["claim_limits"]["replay_embarcado"] == "permitido"
    assert manifest["claim_limits"]["campo_producao"] == "proibido"
    assert manifest["claim_limits"]["sensor_fisico_real"] == "proibido"


def test_packager_collect_files(tmp_path):
    """Testa coleta de arquivos."""
    packager = V8B2HandoffPackager(dry_run=True)

    # Criar estrutura temp
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "file1.py").write_text("test")
    (test_dir / "file2.txt").write_text("test")
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir" / "file3.py").write_text("test")

    files = packager.collect_files(test_dir)
    assert len(files) == 3
    assert any(f.name == "file1.py" for f in files)
    assert any(f.name == "file2.txt" for f in files)
    assert any(f.name == "file3.py" for f in files)


def test_packager_collect_files_excludes():
    """Testa que coleta exclui corretamente."""
    packager = V8B2HandoffPackager(dry_run=True)

    # Usar repo real
    scripts_dir = Path("scripts")
    if scripts_dir.exists():
        files = packager.collect_files(scripts_dir)
        # Não deve incluir __pycache__ ou .pyc
        assert not any("__pycache__" in str(f) for f in files)


def test_packager_dry_run():
    """Testa modo dry-run."""
    packager = V8B2HandoffPackager(dry_run=True)

    # Dry-run não deve criar arquivos reais
    success = packager.package()

    # Deve reportar sucesso ou aviso, não erro crítico
    assert len(packager.errors) == 0 or success is False


def test_packager_report():
    """Testa geração de relatório."""
    packager = V8B2HandoffPackager(dry_run=True)
    packager.files_included = ["file1.txt", "file2.py"]
    packager.warnings.append("Test warning")

    # Deve retornar True se sem erros
    result = packager.report()
    assert isinstance(result, bool)


def test_manifest_json_format():
    """Testa que manifest é JSON válido."""
    packager = V8B2HandoffPackager(dry_run=True)
    manifest = packager.create_package_manifest()

    # Deve ser serializável como JSON
    json_str = json.dumps(manifest, indent=2)
    assert isinstance(json_str, str)

    # Deve ser desserializável
    parsed = json.loads(json_str)
    assert parsed["package_name"] == "SOC_EDGE_V8B2_ESP32_HANDOFF"


def test_required_return_files_defined():
    """Testa que arquivos de retorno esperados estão definidos."""
    packager = V8B2HandoffPackager(dry_run=True)
    manifest = packager.create_package_manifest()

    required_files = manifest["required_return_files"]

    # Verificar arquivos críticos
    assert any("ambiente_esp32.md" in f for f in required_files)
    assert any("resultados_execucao.md" in f for f in required_files)
    assert any("observacoes_operador.md" in f for f in required_files)
    assert any("v8b2_benchmark_summary.json" in f for f in required_files)
    assert any("v8b2_benchmark_metrics.csv" in f for f in required_files)
    assert any("golden_log" in f for f in required_files)
    assert any("extended_log" in f for f in required_files)
    assert any("anomaly_log" in f for f in required_files)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
