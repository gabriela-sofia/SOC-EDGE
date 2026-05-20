"""
Features matemáticas de janela e ciclo para pipeline offline SOC.

Este módulo fornece funções puras para engenharia de features baseadas em:
- Deltas (diferenças temporais de primeira ordem)
- Slopes (taxa de mudança)
- Carga acumulada (integral de corrente)
- Energia acumulada (integral de potência)
- Rolling statistics (média, desvio, min, max, skew)

Todas as funções trabalham com listas de dicionários ou sem depender de pandas,
permitindo uso em contextos embarcados ou stream futuros.
"""

import statistics
from typing import List, Dict, Optional, Any, Tuple


def safe_diff(current: Optional[float], previous: Optional[float]) -> float:
    """
    Calcular diferença segura entre dois valores.

    Retorna 0 se qualquer um for None ou se for a primeira amostra.
    """
    if current is None or previous is None:
        return 0.0
    return float(current - previous)


def safe_dt(current_time: Optional[float], previous_time: Optional[float]) -> float:
    """
    Calcular diferença de tempo segura.

    Retorna 0 se qualquer um for None ou se for a primeira amostra.
    """
    if current_time is None or previous_time is None:
        return 0.0
    dt = float(current_time - previous_time)
    return max(0.0, dt)


def current_ma_to_a(current_ma: Optional[float]) -> float:
    """
    Converter corrente de mA para A.

    Retorna 0 se None.
    """
    if current_ma is None:
        return 0.0
    return float(current_ma) / 1000.0


def charge_increment_ah(
    current_ma: Optional[float],
    dt_s: float,
    use_absolute: bool = True
) -> float:
    """
    Calcular incremento de carga em Ah.

    charge_increment_ah = abs(current_A) * dt_s / 3600

    Retorna 0 se current_ma for None ou dt_s <= 0.
    """
    if current_ma is None or dt_s <= 0:
        return 0.0

    current_a = current_ma_to_a(current_ma)
    if use_absolute:
        current_a = abs(current_a)

    return current_a * dt_s / 3600.0


def energy_increment_wh(
    voltage_v: Optional[float],
    current_ma: Optional[float],
    dt_s: float,
    use_absolute: bool = True
) -> float:
    """
    Calcular incremento de energia em Wh.

    energy_increment_wh = voltage_v * abs(current_A) * dt_s / 3600

    Retorna 0 se voltage_v ou current_ma forem None, ou se dt_s <= 0.
    """
    if voltage_v is None or current_ma is None or dt_s <= 0:
        return 0.0

    voltage = float(voltage_v)
    current_a = current_ma_to_a(current_ma)
    if use_absolute:
        current_a = abs(current_a)

    return voltage * current_a * dt_s / 3600.0


def slope_delta(
    value_current: Optional[float],
    value_previous: Optional[float],
    dt_s: float
) -> Optional[float]:
    """
    Calcular slope (taxa de mudança por segundo).

    slope = (value_current - value_previous) / dt_s

    Retorna None se dt_s <= 0 ou se valores forem None.
    Retorna 0 para primeira amostra de um grupo (dt_s == 0).
    """
    if value_current is None or value_previous is None:
        return None

    if dt_s <= 0:
        return None

    delta = float(value_current - value_previous)
    return delta / dt_s


def rolling_mean(values: List[Optional[float]]) -> Optional[float]:
    """
    Calcular média de uma lista de valores.

    Ignora None. Retorna None se lista vazia ou sem valores válidos.
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def rolling_std(values: List[Optional[float]]) -> Optional[float]:
    """
    Calcular desvio padrão de uma lista de valores.

    Ignora None. Retorna None se < 2 valores válidos.
    """
    valid = [float(v) for v in values if v is not None]
    if len(valid) < 2:
        return None
    return statistics.stdev(valid)


def rolling_min(values: List[Optional[float]]) -> Optional[float]:
    """
    Calcular mínimo de uma lista de valores.

    Ignora None. Retorna None se vazia.
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return min(valid)


def rolling_max(values: List[Optional[float]]) -> Optional[float]:
    """
    Calcular máximo de uma lista de valores.

    Ignora None. Retorna None se vazia.
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return max(valid)


def rolling_skew(values: List[Optional[float]]) -> Optional[float]:
    """
    Calcular skewness (assimetria) de uma lista de valores.

    Ignora None. Retorna None se < 3 valores válidos.
    Usa fórmula simplificada de skewness.
    """
    valid = [float(v) for v in values if v is not None]
    if len(valid) < 3:
        return None

    mean = sum(valid) / len(valid)
    std = statistics.stdev(valid)

    if std == 0:
        return 0.0

    skew = sum(((x - mean) ** 3 for x in valid)) / (len(valid) * (std ** 3))
    return skew


def compute_first_order_deltas(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Adicionar deltas (diferenças temporais) a cada linha.

    Adiciona colunas:
    - delta_voltage (V)
    - delta_current (mA)
    - delta_temperature (C)
    - dt_s (segundos)

    Primeira amostra de cada grupo terá deltas = 0.
    Grupos são identificados por 'cell_id' e/ou 'cycle_id' se presentes.
    """
    if not rows:
        return rows

    result = []
    last_row = None
    last_group_key = None

    for row in rows:
        row_copy = dict(row)

        # Identificar se mudou de grupo
        group_key = (row.get("cell_id"), row.get("cycle_id"))
        changed_group = (group_key != last_group_key)

        if changed_group or last_row is None:
            # Primeira amostra do grupo
            row_copy["delta_voltage"] = 0.0
            row_copy["delta_current"] = 0.0
            row_copy["delta_temperature"] = 0.0
            row_copy["dt_s"] = 0.0
        else:
            # Calcular deltas
            time_col = row.get("timestamp_s") if "timestamp_s" in row else row.get("elapsed_time_s")
            last_time_col = last_row.get("timestamp_s") if "timestamp_s" in last_row else last_row.get("elapsed_time_s")
            dt = safe_dt(time_col, last_time_col)

            row_copy["delta_voltage"] = safe_diff(
                row.get("voltage_v"),
                last_row.get("voltage_v")
            )
            row_copy["delta_current"] = safe_diff(
                row.get("current_ma"),
                last_row.get("current_ma")
            )
            row_copy["delta_temperature"] = safe_diff(
                row.get("temperature_c"),
                last_row.get("temperature_c")
            )
            row_copy["dt_s"] = dt

        result.append(row_copy)
        last_row = row_copy
        last_group_key = group_key

    return result


def compute_cycle_cumulative_features(
    rows: List[Dict[str, Any]],
    group_keys: Tuple[str, ...] = ("cell_id", "cycle_id")
) -> List[Dict[str, Any]]:
    """
    Adicionar features cumulativas por ciclo.

    Adiciona colunas:
    - cumulative_charge_ah (integral de carga acumulada)
    - cumulative_energy_wh (integral de energia acumulada)

    Acumuladores reiniciam quando cell_id ou cycle_id muda.
    Requer colunas: voltage_v, current_ma, dt_s, delta_* (de compute_first_order_deltas).
    """
    if not rows:
        return rows

    result = []
    cumulative_charge = 0.0
    cumulative_energy = 0.0
    last_group_key = None

    for row in rows:
        row_copy = dict(row)

        # Verificar mudança de grupo
        group_key = tuple(row.get(k) for k in group_keys if k in row)
        if group_key != last_group_key:
            cumulative_charge = 0.0
            cumulative_energy = 0.0

        # Obter dt_s de deltas já computados
        dt = row.get("dt_s", 0.0)

        # Incrementar acumuladores
        charge_inc = charge_increment_ah(
            row.get("current_ma"),
            dt,
            use_absolute=True
        )
        energy_inc = energy_increment_wh(
            row.get("voltage_v"),
            row.get("current_ma"),
            dt,
            use_absolute=True
        )

        cumulative_charge += charge_inc
        cumulative_energy += energy_inc

        row_copy["cumulative_charge_ah"] = cumulative_charge
        row_copy["cumulative_energy_wh"] = cumulative_energy

        result.append(row_copy)
        last_group_key = group_key

    return result


def compute_rolling_features(
    rows: List[Dict[str, Any]],
    window_size: int = 5
) -> List[Dict[str, Any]]:
    """
    Adicionar rolling statistics para voltage, current e temperature.

    Janela causal: para cada amostra, usa até window_size amostras anteriores.

    Adiciona colunas:
    - rolling_voltage_mean, rolling_voltage_std, rolling_voltage_min, max, skew
    - rolling_current_mean, rolling_current_std, rolling_current_min, max, skew
    - rolling_temperature_mean, rolling_temperature_std, rolling_temperature_min, max, skew

    Se < window_size amostras anteriores, usa o que tem.
    """
    if not rows or window_size <= 0:
        return rows

    result = []

    for i, row in enumerate(rows):
        row_copy = dict(row)

        # Definir janela causal: [max(0, i - window_size + 1), i]
        start_idx = max(0, i - window_size + 1)
        window = rows[start_idx:i + 1]

        # Extrair valores da janela
        voltages = [r.get("voltage_v") for r in window]
        currents = [r.get("current_ma") for r in window]
        temperatures = [r.get("temperature_c") for r in window]

        # Calcular rolling stats
        row_copy["rolling_voltage_mean"] = rolling_mean(voltages)
        row_copy["rolling_voltage_std"] = rolling_std(voltages)
        row_copy["rolling_voltage_min"] = rolling_min(voltages)
        row_copy["rolling_voltage_max"] = rolling_max(voltages)
        row_copy["rolling_voltage_skew"] = rolling_skew(voltages)

        row_copy["rolling_current_mean"] = rolling_mean(currents)
        row_copy["rolling_current_std"] = rolling_std(currents)
        row_copy["rolling_current_min"] = rolling_min(currents)
        row_copy["rolling_current_max"] = rolling_max(currents)
        row_copy["rolling_current_skew"] = rolling_skew(currents)

        row_copy["rolling_temperature_mean"] = rolling_mean(temperatures)
        row_copy["rolling_temperature_std"] = rolling_std(temperatures)
        row_copy["rolling_temperature_min"] = rolling_min(temperatures)
        row_copy["rolling_temperature_max"] = rolling_max(temperatures)
        row_copy["rolling_temperature_skew"] = rolling_skew(temperatures)

        result.append(row_copy)

    return result


def compute_slopes(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Adicionar slopes (taxa de mudança por segundo).

    Requer colunas: voltage_v, current_ma, temperature_c, dt_s.

    Adiciona colunas:
    - voltage_slope_v_per_s
    - current_slope_ma_per_s
    - temperature_slope_c_per_s
    """
    if not rows:
        return rows

    result = []
    last_row = None

    for row in rows:
        row_copy = dict(row)
        dt = row.get("dt_s", 0.0)

        if last_row is None or dt <= 0:
            row_copy["voltage_slope_v_per_s"] = None
            row_copy["current_slope_ma_per_s"] = None
            row_copy["temperature_slope_c_per_s"] = None
        else:
            row_copy["voltage_slope_v_per_s"] = slope_delta(
                row.get("voltage_v"),
                last_row.get("voltage_v"),
                dt
            )
            row_copy["current_slope_ma_per_s"] = slope_delta(
                row.get("current_ma"),
                last_row.get("current_ma"),
                dt
            )
            row_copy["temperature_slope_c_per_s"] = slope_delta(
                row.get("temperature_c"),
                last_row.get("temperature_c"),
                dt
            )

        result.append(row_copy)
        last_row = row_copy

    return result


def compute_increment_features(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Adicionar features de incremento (carga e energia).

    Requer colunas: voltage_v, current_ma, dt_s.

    Adiciona colunas:
    - charge_increment_ah
    - energy_increment_wh
    """
    if not rows:
        return rows

    result = []

    for row in rows:
        row_copy = dict(row)
        dt = row.get("dt_s", 0.0)

        row_copy["charge_increment_ah"] = charge_increment_ah(
            row.get("current_ma"),
            dt,
            use_absolute=True
        )
        row_copy["energy_increment_wh"] = energy_increment_wh(
            row.get("voltage_v"),
            row.get("current_ma"),
            dt,
            use_absolute=True
        )

        result.append(row_copy)

    return result


def compute_all_features(
    rows: List[Dict[str, Any]],
    window_size: int = 5,
    group_keys: Tuple[str, ...] = ("cell_id", "cycle_id")
) -> List[Dict[str, Any]]:
    """
    Pipeline completo de engenharia de features.

    Executa em ordem:
    1. Deltas temporais
    2. Slopes
    3. Incrementos (carga/energia)
    4. Features cumulativas por ciclo
    5. Rolling statistics

    Retorna lista de dicts com todas as colunas originais + features.
    """
    result = rows
    result = compute_first_order_deltas(result)
    result = compute_slopes(result)
    result = compute_increment_features(result)
    result = compute_cycle_cumulative_features(result, group_keys=group_keys)
    result = compute_rolling_features(result, window_size=window_size)
    return result
