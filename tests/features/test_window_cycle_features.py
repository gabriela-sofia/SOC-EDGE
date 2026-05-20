"""
Testes para src/features/window_cycle_features.py

Testa funções matemáticas puras sem dependência de pandas.
"""

import pytest
from src.features.window_cycle_features import (
    safe_diff,
    safe_dt,
    current_ma_to_a,
    charge_increment_ah,
    energy_increment_wh,
    slope_delta,
    rolling_mean,
    rolling_std,
    rolling_min,
    rolling_max,
    rolling_skew,
    compute_first_order_deltas,
    compute_cycle_cumulative_features,
    compute_rolling_features,
    compute_slopes,
    compute_increment_features,
    compute_all_features,
)


class TestBasicConversions:
    """Teste conversões básicas."""

    def test_current_ma_to_a_positive(self):
        assert current_ma_to_a(1000.0) == 1.0

    def test_current_ma_to_a_zero(self):
        assert current_ma_to_a(0.0) == 0.0

    def test_current_ma_to_a_negative(self):
        assert current_ma_to_a(-500.0) == -0.5

    def test_current_ma_to_a_none(self):
        assert current_ma_to_a(None) == 0.0


class TestSafeDiff:
    """Teste diferença segura."""

    def test_normal_diff(self):
        assert safe_diff(5.0, 3.0) == 2.0

    def test_negative_diff(self):
        assert safe_diff(1.0, 5.0) == -4.0

    def test_none_current(self):
        assert safe_diff(None, 3.0) == 0.0

    def test_none_previous(self):
        assert safe_diff(5.0, None) == 0.0

    def test_both_none(self):
        assert safe_diff(None, None) == 0.0


class TestSafeDt:
    """Teste diferença de tempo segura."""

    def test_normal_dt(self):
        assert safe_dt(10.0, 5.0) == 5.0

    def test_zero_dt(self):
        assert safe_dt(5.0, 5.0) == 0.0

    def test_negative_dt_clamped(self):
        assert safe_dt(3.0, 5.0) == 0.0

    def test_none_current(self):
        assert safe_dt(None, 5.0) == 0.0


class TestChargeIncrement:
    """Teste incremento de carga."""

    def test_charge_positive_current(self):
        # 1000 mA = 1 A, 3600 s = 1 h, então 1 A * 1 h = 1 Ah
        result = charge_increment_ah(1000.0, 3600.0, use_absolute=True)
        assert abs(result - 1.0) < 1e-6

    def test_charge_negative_current_absolute(self):
        # -1000 mA com absolute=True → 1 A
        result = charge_increment_ah(-1000.0, 3600.0, use_absolute=True)
        assert abs(result - 1.0) < 1e-6

    def test_charge_zero_time(self):
        assert charge_increment_ah(1000.0, 0.0, use_absolute=True) == 0.0

    def test_charge_none_current(self):
        assert charge_increment_ah(None, 3600.0, use_absolute=True) == 0.0

    def test_charge_small_time(self):
        # 1 A, 1 segundo → 1/3600 Ah
        result = charge_increment_ah(1000.0, 1.0, use_absolute=True)
        assert abs(result - (1.0 / 3600.0)) < 1e-6


class TestEnergyIncrement:
    """Teste incremento de energia."""

    def test_energy_calculation(self):
        # 4.2 V, 1000 mA (1 A), 3600 s = 4.2 Wh
        result = energy_increment_wh(4.2, 1000.0, 3600.0, use_absolute=True)
        assert abs(result - 4.2) < 1e-6

    def test_energy_zero_voltage(self):
        assert energy_increment_wh(0.0, 1000.0, 3600.0, use_absolute=True) == 0.0

    def test_energy_zero_time(self):
        assert energy_increment_wh(4.2, 1000.0, 0.0, use_absolute=True) == 0.0

    def test_energy_none_voltage(self):
        assert energy_increment_wh(None, 1000.0, 3600.0, use_absolute=True) == 0.0


class TestSlopeDelta:
    """Teste cálculo de slope."""

    def test_slope_normal(self):
        # (5.0 - 4.0) / 2.0 = 0.5
        result = slope_delta(5.0, 4.0, 2.0)
        assert abs(result - 0.5) < 1e-6

    def test_slope_zero_dt(self):
        assert slope_delta(5.0, 4.0, 0.0) is None

    def test_slope_negative_dt(self):
        assert slope_delta(5.0, 4.0, -1.0) is None

    def test_slope_none_current(self):
        assert slope_delta(None, 4.0, 2.0) is None

    def test_slope_none_previous(self):
        assert slope_delta(5.0, None, 2.0) is None


class TestRollingMean:
    """Teste média móvel."""

    def test_mean_simple(self):
        result = rolling_mean([1.0, 2.0, 3.0])
        assert abs(result - 2.0) < 1e-6

    def test_mean_with_none(self):
        result = rolling_mean([1.0, None, 3.0])
        assert abs(result - 2.0) < 1e-6

    def test_mean_all_none(self):
        assert rolling_mean([None, None]) is None

    def test_mean_empty(self):
        assert rolling_mean([]) is None


class TestRollingStd:
    """Teste desvio padrão móvel."""

    def test_std_simple(self):
        result = rolling_std([1.0, 2.0, 3.0])
        assert result is not None
        assert result > 0

    def test_std_one_value(self):
        assert rolling_std([1.0]) is None

    def test_std_two_values(self):
        result = rolling_std([1.0, 3.0])
        assert result is not None
        assert abs(result - (2.0 ** 0.5)) < 1e-3

    def test_std_with_none(self):
        result = rolling_std([1.0, None, 3.0])
        assert result is not None


class TestRollingMinMax:
    """Teste min/max móvel."""

    def test_min(self):
        assert rolling_min([3.0, 1.0, 2.0]) == 1.0

    def test_max(self):
        assert rolling_max([3.0, 1.0, 2.0]) == 3.0

    def test_min_with_none(self):
        assert rolling_min([3.0, None, 1.0]) == 1.0

    def test_max_empty(self):
        assert rolling_max([]) is None


class TestRollingSkew:
    """Teste assimetria móvel."""

    def test_skew_simple(self):
        result = rolling_skew([1.0, 2.0, 3.0])
        assert result is not None
        assert result == 0.0  # Simétrica

    def test_skew_insufficient_values(self):
        assert rolling_skew([1.0, 2.0]) is None

    def test_skew_with_none(self):
        result = rolling_skew([1.0, None, 2.0, 3.0])
        assert result is not None


class TestComputeFirstOrderDeltas:
    """Teste cálculo de deltas."""

    def test_deltas_single_row(self):
        rows = [
            {"voltage_v": 4.2, "current_ma": 100.0, "temperature_c": 25.0, "timestamp_s": 0.0}
        ]
        result = compute_first_order_deltas(rows)
        assert len(result) == 1
        assert result[0]["delta_voltage"] == 0.0
        assert result[0]["delta_current"] == 0.0
        assert result[0]["delta_temperature"] == 0.0
        assert result[0]["dt_s"] == 0.0

    def test_deltas_two_rows_same_group(self):
        rows = [
            {"voltage_v": 4.0, "current_ma": 100.0, "temperature_c": 25.0, "timestamp_s": 0.0, "cell_id": "C1", "cycle_id": 1},
            {"voltage_v": 4.2, "current_ma": 150.0, "temperature_c": 26.0, "timestamp_s": 1.0, "cell_id": "C1", "cycle_id": 1},
        ]
        result = compute_first_order_deltas(rows)
        assert abs(result[1]["delta_voltage"] - 0.2) < 1e-6
        assert abs(result[1]["delta_current"] - 50.0) < 1e-6
        assert abs(result[1]["delta_temperature"] - 1.0) < 1e-6
        # dt_s deve ser positivo, próximo de 1.0
        assert result[1]["dt_s"] >= 0.0
        assert abs(result[1]["dt_s"] - 1.0) < 0.1

    def test_deltas_group_reset(self):
        rows = [
            {"voltage_v": 4.0, "current_ma": 100.0, "temperature_c": 25.0, "timestamp_s": 0.0, "cell_id": "C1", "cycle_id": 1},
            {"voltage_v": 4.2, "current_ma": 150.0, "temperature_c": 26.0, "timestamp_s": 1.0, "cell_id": "C1", "cycle_id": 2},
        ]
        result = compute_first_order_deltas(rows)
        # Ao trocar cycle_id, deltas devem ser 0
        assert result[1]["delta_voltage"] == 0.0
        assert result[1]["delta_current"] == 0.0
        assert result[1]["delta_temperature"] == 0.0
        assert result[1]["dt_s"] == 0.0


class TestComputeCycleCumulativeFeatures:
    """Teste features cumulativas por ciclo."""

    def test_cumulative_single_row(self):
        rows = [
            {
                "voltage_v": 4.0,
                "current_ma": 100.0,
                "temperature_c": 25.0,
                "dt_s": 1.0,
                "cell_id": "C1",
                "cycle_id": 1,
            }
        ]
        result = compute_cycle_cumulative_features(rows, group_keys=("cell_id", "cycle_id"))
        assert result[0]["cumulative_charge_ah"] >= 0.0
        assert result[0]["cumulative_energy_wh"] >= 0.0

    def test_cumulative_reset_on_cycle_change(self):
        rows = [
            {
                "voltage_v": 4.0,
                "current_ma": 100.0,
                "temperature_c": 25.0,
                "dt_s": 1.0,
                "cell_id": "C1",
                "cycle_id": 1,
            },
            {
                "voltage_v": 4.0,
                "current_ma": 100.0,
                "temperature_c": 25.0,
                "dt_s": 1.0,
                "cell_id": "C1",
                "cycle_id": 2,
            },
        ]
        result = compute_cycle_cumulative_features(rows, group_keys=("cell_id", "cycle_id"))
        # Ao trocar cycle, acumulador deve resetar
        first_cycle_cumul = result[0]["cumulative_charge_ah"]
        second_cycle_cumul = result[1]["cumulative_charge_ah"]
        # Ambos têm o mesmo incremento (100 mA * 1 s = 0.027 Ah)
        # Mas na primeira linha do ciclo, seria 0.027; na primeira do segundo ciclo, também é 0.027
        # O ponto é que reseta (não acumula sobre o ciclo anterior)
        assert abs(first_cycle_cumul - second_cycle_cumul) < 1e-3


class TestComputeRollingFeatures:
    """Teste rolling features."""

    def test_rolling_window_size_one(self):
        rows = [
            {"voltage_v": 4.0, "current_ma": 100.0, "temperature_c": 25.0},
            {"voltage_v": 4.2, "current_ma": 150.0, "temperature_c": 26.0},
        ]
        result = compute_rolling_features(rows, window_size=1)
        assert len(result) == 2
        # Com window_size=1, rolling_mean deveria ser igual ao valor atual
        assert result[0]["rolling_voltage_mean"] == 4.0
        assert result[1]["rolling_voltage_mean"] == 4.2

    def test_rolling_with_window_size_5(self):
        rows = [
            {"voltage_v": 4.0 + i * 0.1, "current_ma": 100.0, "temperature_c": 25.0}
            for i in range(10)
        ]
        result = compute_rolling_features(rows, window_size=5)
        assert len(result) == 10
        # Todas as rolling features devem estar preenchidas
        for row in result:
            assert row["rolling_voltage_mean"] is not None


class TestComputeAllFeatures:
    """Teste pipeline completo de features."""

    def test_all_features_complete_pipeline(self):
        rows = [
            {
                "sample_id": 1,
                "voltage_v": 4.0,
                "current_ma": 100.0,
                "temperature_c": 25.0,
                "timestamp_s": 0.0,
                "cell_id": "C1",
                "cycle_id": 1,
            },
            {
                "sample_id": 2,
                "voltage_v": 4.1,
                "current_ma": 120.0,
                "temperature_c": 25.5,
                "timestamp_s": 1.0,
                "cell_id": "C1",
                "cycle_id": 1,
            },
            {
                "sample_id": 3,
                "voltage_v": 4.2,
                "current_ma": 150.0,
                "temperature_c": 26.0,
                "timestamp_s": 2.0,
                "cell_id": "C1",
                "cycle_id": 1,
            },
        ]

        result = compute_all_features(rows, window_size=2, group_keys=("cell_id", "cycle_id"))

        assert len(result) == 3
        # Verificar que todas as colunas de features foram adicionadas
        expected_features = [
            "delta_voltage", "delta_current", "delta_temperature", "dt_s",
            "voltage_slope_v_per_s", "current_slope_ma_per_s", "temperature_slope_c_per_s",
            "charge_increment_ah", "energy_increment_wh",
            "cumulative_charge_ah", "cumulative_energy_wh",
            "rolling_voltage_mean", "rolling_voltage_std", "rolling_voltage_min", "rolling_voltage_max", "rolling_voltage_skew",
            "rolling_current_mean", "rolling_current_std", "rolling_current_min", "rolling_current_max", "rolling_current_skew",
            "rolling_temperature_mean", "rolling_temperature_std", "rolling_temperature_min", "rolling_temperature_max", "rolling_temperature_skew",
        ]
        for feature in expected_features:
            assert feature in result[0], f"Feature {feature} not found in result"

        # Primeira amostra deve ter deltas = 0
        assert result[0]["delta_voltage"] == 0.0
        assert result[0]["delta_current"] == 0.0
        assert result[0]["dt_s"] == 0.0

        # Verificar que carga acumulada está crescendo
        assert result[1]["cumulative_charge_ah"] >= result[0]["cumulative_charge_ah"]
        assert result[2]["cumulative_charge_ah"] >= result[1]["cumulative_charge_ah"]
