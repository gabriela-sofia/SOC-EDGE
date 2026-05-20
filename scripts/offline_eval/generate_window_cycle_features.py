#!/usr/bin/env python3
"""
Gerar features matemáticas de janela/ciclo a partir de CSV.

Uso:
    python scripts/offline_eval/generate_window_cycle_features.py \\
        --input <csv_path> \\
        [--output <csv_path>] \\
        [--window-size <int>] \\
        [--time-column <str>] \\
        [--group-cols <col1,col2>]

Requer colunas mínimas: voltage_v, current_ma, temperature_c, e uma coluna de tempo.
"""

import argparse
import csv
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.features.window_cycle_features import compute_all_features


def read_csv_as_dicts(filepath: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Ler CSV e retornar lista de dicts e lista de fieldnames.

    Converte colunas numéricas para float quando possível.
    """
    rows = []
    fieldnames = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        for row in reader:
            # Converter valores numéricos
            converted = {}
            for key, value in row.items():
                if value == "" or value is None:
                    converted[key] = None
                else:
                    try:
                        converted[key] = float(value)
                    except ValueError:
                        converted[key] = value
            rows.append(converted)

    return rows, fieldnames


def write_csv_from_dicts(
    filepath: str,
    rows: List[Dict[str, Any]],
    fieldnames: List[str]
) -> None:
    """
    Escrever lista de dicts em CSV.

    Cria diretório pai se não existir.
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def detect_time_column(fieldnames: List[str]) -> Optional[str]:
    """
    Detectar coluna de tempo automaticamente.

    Prioridade: timestamp_s > elapsed_time_s.
    """
    if "timestamp_s" in fieldnames:
        return "timestamp_s"
    if "elapsed_time_s" in fieldnames:
        return "elapsed_time_s"
    return None


def detect_group_columns(fieldnames: List[str]) -> List[str]:
    """
    Detectar colunas de grupo automaticamente.

    Retorna ['cell_id', 'cycle_id'] se ambas existirem.
    Senão tenta retornar ['cycle_id'] ou vazio.
    """
    cols = []
    if "cell_id" in fieldnames:
        cols.append("cell_id")
    if "cycle_id" in fieldnames:
        cols.append("cycle_id")
    return cols if cols else []


def validate_required_columns(
    fieldnames: List[str],
    time_column: Optional[str]
) -> Tuple[bool, str]:
    """
    Validar se CSV tem colunas mínimas obrigatórias.

    Retorna (is_valid, message).
    """
    required = ["voltage_v", "current_ma", "temperature_c"]
    missing = [col for col in required if col not in fieldnames]

    if missing:
        return False, f"Colunas obrigatórias faltando: {', '.join(missing)}"

    if not time_column:
        return False, "Coluna de tempo não encontrada (timestamp_s ou elapsed_time_s)."

    return True, "OK"


def main():
    parser = argparse.ArgumentParser(
        description="Gerar features matemáticas de janela/ciclo a partir de CSV."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Caminho do CSV de entrada."
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Caminho do CSV de saída. Padrão: local_runs/features/window_cycle_features.csv"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=5,
        help="Tamanho da janela rolling. Padrão: 5"
    )
    parser.add_argument(
        "--time-column",
        default=None,
        help="Nome da coluna de tempo. Auto se não especificado."
    )
    parser.add_argument(
        "--group-cols",
        default=None,
        help="Colunas de grupo (separadas por vírgula). Auto se não especificado."
    )

    args = parser.parse_args()

    # Ler CSV
    try:
        rows, fieldnames = read_csv_as_dicts(args.input)
    except FileNotFoundError:
        print(f"Erro: arquivo não encontrado: {args.input}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Erro ao ler CSV: {e}", file=sys.stderr)
        return 1

    if not rows:
        print("Erro: CSV vazio.", file=sys.stderr)
        return 1

    # Detectar/validar coluna de tempo
    time_column = args.time_column or detect_time_column(fieldnames)

    # Validar colunas obrigatórias
    is_valid, msg = validate_required_columns(fieldnames, time_column)
    if not is_valid:
        print(f"Erro: {msg}", file=sys.stderr)
        return 1

    # Preparar rows para garantir consistência na coluna de tempo
    for row in rows:
        if time_column not in row or row[time_column] is None:
            row[time_column] = None

    # Detectar/validar colunas de grupo
    if args.group_cols:
        group_cols = tuple(args.group_cols.split(","))
    else:
        group_cols = tuple(detect_group_columns(fieldnames))

    # Computar features
    try:
        result_rows = compute_all_features(
            rows,
            window_size=args.window_size,
            group_keys=group_cols
        )
    except Exception as e:
        print(f"Erro ao computar features: {e}", file=sys.stderr)
        return 1

    # Preparar fieldnames de saída
    if result_rows:
        output_fieldnames = list(result_rows[0].keys())
    else:
        output_fieldnames = fieldnames

    # Definir caminho de saída
    if args.output is None:
        output_path = "local_runs/features/window_cycle_features.csv"
    else:
        output_path = args.output

    # Escrever CSV de saída
    try:
        write_csv_from_dicts(output_path, result_rows, output_fieldnames)
    except Exception as e:
        print(f"Erro ao escrever CSV de saída: {e}", file=sys.stderr)
        return 1

    # Imprimir resumo
    features_generated = [
        col for col in output_fieldnames
        if col not in fieldnames
    ]

    groups_detected = detect_group_columns(fieldnames)
    if not groups_detected:
        groups_detected = ["sem grupo (todas amostras em um grupo)"]

    print(f"Linhas de entrada: {len(rows)}")
    print(f"Linhas de saída: {len(result_rows)}")
    print(f"Features geradas: {len(features_generated)}")
    print(f"Grupos detectados: {', '.join(groups_detected)}")
    print(f"Window size: {args.window_size}")
    print(f"Output: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
