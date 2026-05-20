"""
Testes para scripts/offline_eval/generate_window_cycle_features.py

Testa geração de features a partir de CSV usando dados sintéticos.
"""

import csv
import tempfile
import subprocess
import sys
from pathlib import Path

import pytest


def create_test_csv(filepath: str) -> None:
    """
    Criar CSV de teste sintético.

    Contém 10 amostras com coluna de tempo e dados de sensores.
    """
    rows = [
        {
            "sample_id": "1",
            "cell_id": "CELL_A",
            "cycle_id": "1",
            "timestamp_s": "0.0",
            "voltage_v": "4.0",
            "current_ma": "100.0",
            "temperature_c": "25.0",
            "soc_method_b": "0.9",
        },
        {
            "sample_id": "2",
            "cell_id": "CELL_A",
            "cycle_id": "1",
            "timestamp_s": "1.0",
            "voltage_v": "4.05",
            "current_ma": "120.0",
            "temperature_c": "25.1",
            "soc_method_b": "0.88",
        },
        {
            "sample_id": "3",
            "cell_id": "CELL_A",
            "cycle_id": "1",
            "timestamp_s": "2.0",
            "voltage_v": "4.10",
            "current_ma": "150.0",
            "temperature_c": "25.2",
            "soc_method_b": "0.85",
        },
        {
            "sample_id": "4",
            "cell_id": "CELL_A",
            "cycle_id": "1",
            "timestamp_s": "3.0",
            "voltage_v": "4.15",
            "current_ma": "100.0",
            "temperature_c": "25.3",
            "soc_method_b": "0.82",
        },
        {
            "sample_id": "5",
            "cell_id": "CELL_A",
            "cycle_id": "1",
            "timestamp_s": "4.0",
            "voltage_v": "4.20",
            "current_ma": "80.0",
            "temperature_c": "25.4",
            "soc_method_b": "0.80",
        },
        {
            "sample_id": "6",
            "cell_id": "CELL_A",
            "cycle_id": "2",
            "timestamp_s": "5.0",
            "voltage_v": "3.5",
            "current_ma": "-100.0",
            "temperature_c": "24.9",
            "soc_method_b": "0.40",
        },
        {
            "sample_id": "7",
            "cell_id": "CELL_A",
            "cycle_id": "2",
            "timestamp_s": "6.0",
            "voltage_v": "3.4",
            "current_ma": "-150.0",
            "temperature_c": "24.8",
            "soc_method_b": "0.30",
        },
        {
            "sample_id": "8",
            "cell_id": "CELL_A",
            "cycle_id": "2",
            "timestamp_s": "7.0",
            "voltage_v": "3.3",
            "current_ma": "-120.0",
            "temperature_c": "24.7",
            "soc_method_b": "0.20",
        },
        {
            "sample_id": "9",
            "cell_id": "CELL_A",
            "cycle_id": "2",
            "timestamp_s": "8.0",
            "voltage_v": "3.2",
            "current_ma": "-80.0",
            "temperature_c": "24.6",
            "soc_method_b": "0.10",
        },
        {
            "sample_id": "10",
            "cell_id": "CELL_A",
            "cycle_id": "2",
            "timestamp_s": "9.0",
            "voltage_v": "3.0",
            "current_ma": "0.0",
            "temperature_c": "24.5",
            "soc_method_b": "0.05",
        },
    ]

    fieldnames = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestGenerateWindowCycleFeatures:
    """Teste geração de features via script."""

    def test_script_with_valid_csv(self, tmp_path):
        """Testar script com CSV válido."""
        input_csv = tmp_path / "test_input.csv"
        output_csv = tmp_path / "test_output.csv"

        create_test_csv(str(input_csv))

        cmd = [
            sys.executable,
            "scripts/offline_eval/generate_window_cycle_features.py",
            "--input", str(input_csv),
            "--output", str(output_csv),
            "--window-size", "3",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Verificar que output foi criado
        assert output_csv.exists()

        # Ler output e verificar colunas
        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 10, f"Expected 10 rows, got {len(rows)}"

        # Verificar que features foram geradas
        expected_features = [
            "delta_voltage", "delta_current", "delta_temperature",
            "cumulative_charge_ah", "cumulative_energy_wh",
            "rolling_voltage_mean",
        ]
        for feature in expected_features:
            assert feature in rows[0], f"Feature {feature} not found in output"

    def test_script_missing_required_column(self, tmp_path):
        """Testar script com coluna obrigatória faltando."""
        input_csv = tmp_path / "test_input_bad.csv"

        # CSV sem voltage_v
        with open(input_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["current_ma", "temperature_c", "timestamp_s"])
            writer.writerow(["100.0", "25.0", "0.0"])

        cmd = [
            sys.executable,
            "scripts/offline_eval/generate_window_cycle_features.py",
            "--input", str(input_csv),
            "--output", str(tmp_path / "output.csv"),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        assert result.returncode == 1, "Script should fail with missing column"

    def test_script_preserves_optional_columns(self, tmp_path):
        """Testar que script preserva colunas opcionais como SOC."""
        input_csv = tmp_path / "test_input_with_soc.csv"
        output_csv = tmp_path / "test_output_with_soc.csv"

        create_test_csv(str(input_csv))

        cmd = [
            sys.executable,
            "scripts/offline_eval/generate_window_cycle_features.py",
            "--input", str(input_csv),
            "--output", str(output_csv),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        assert result.returncode == 0

        # Verificar que soc_method_b foi preservado
        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert "soc_method_b" in rows[0]
        assert float(rows[0]["soc_method_b"]) > 0

    def test_script_output_default_path(self, tmp_path):
        """Testar que output padrão vai para local_runs/features/."""
        input_csv = tmp_path / "test_input.csv"
        create_test_csv(str(input_csv))

        # Mudar para diretório temporário para não poluir local_runs
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            cmd = [
                sys.executable,
                str(Path(old_cwd) / "scripts/offline_eval/generate_window_cycle_features.py"),
                "--input", str(input_csv),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            assert result.returncode == 0

            # Verificar que output foi para local_runs/features/
            # (em tmp_path em vez do real local_runs)
            default_output = tmp_path / "local_runs" / "features" / "window_cycle_features.csv"
            assert default_output.exists()
        finally:
            os.chdir(old_cwd)

    def test_script_detects_groups(self, tmp_path):
        """Testar que script detecta cell_id e cycle_id automaticamente."""
        input_csv = tmp_path / "test_grouped.csv"
        output_csv = tmp_path / "test_grouped_output.csv"

        create_test_csv(str(input_csv))

        cmd = [
            sys.executable,
            "scripts/offline_eval/generate_window_cycle_features.py",
            "--input", str(input_csv),
            "--output", str(output_csv),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        assert result.returncode == 0

        # Script deveria ter detectado cell_id e cycle_id
        assert "cell_id" in result.stdout or "cycle_id" in result.stdout or "Grupos detectados" in result.stdout

    def test_cumulative_resets_on_cycle_change(self, tmp_path):
        """Testar que carga acumulada reseta ao mudar cycle_id."""
        input_csv = tmp_path / "test_cumul.csv"
        output_csv = tmp_path / "test_cumul_output.csv"

        create_test_csv(str(input_csv))

        cmd = [
            sys.executable,
            "scripts/offline_eval/generate_window_cycle_features.py",
            "--input", str(input_csv),
            "--output", str(output_csv),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        assert result.returncode == 0

        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Row 5 deve ter cycle_id=2 (muda de ciclo)
        # cumulative_charge deve ser menor ou == 0 pois é novo ciclo
        cumul_before = float(rows[4]["cumulative_charge_ah"])
        cumul_after = float(rows[5]["cumulative_charge_ah"])

        # Após mudança de ciclo, acumulador deve resetar
        assert cumul_after <= cumul_before or abs(cumul_after) < 1e-6
