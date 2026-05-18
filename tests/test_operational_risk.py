"""
Unit Tests for Smart Pole Operational Risk Layer

Test coverage:
- Usable capacity estimation
- Energy remaining calculation
- Autonomy estimation
- Risk classification
- Mode selection
- Edge cases (NaN, invalid inputs, extreme values)
- Integration tests (full update pipeline)

Reference: REPORTS/29_SMART_POLE_OPERATIONAL_RISK_LAYER_SPEC.md Part 9

Author: SOC Project Team
Date: 2026-05-07
"""

import pytest
import numpy as np
from src.risk_layer.operational_risk import (
    SmartPoleRiskLayer,
    estimate_usable_capacity_ah,
    estimate_remaining_energy_wh,
    estimate_autonomy_h,
    classify_risk,
)


class TestUsableCapacity:
    """Test capacity estimation based on SOH."""

    def test_nominal_capacity_new_battery(self):
        """New battery (SOH=1.0) should give full nominal capacity."""
        result = estimate_usable_capacity_ah(soh=1.0, nominal_ah=100)
        assert result == 100.0

    def test_degraded_capacity(self):
        """Degraded battery (SOH=0.95) should give reduced capacity."""
        result = estimate_usable_capacity_ah(soh=0.95, nominal_ah=100)
        assert result == pytest.approx(95.0)

    def test_eol_capacity(self):
        """EOL battery (SOH=0.80) should give 80% capacity."""
        result = estimate_usable_capacity_ah(soh=0.80, nominal_ah=100)
        assert result == pytest.approx(80.0)

    def test_invalid_soh_nan(self):
        """NaN SOH should return nominal capacity (fallback)."""
        result = estimate_usable_capacity_ah(soh=np.nan, nominal_ah=100)
        assert result == 100.0

    def test_invalid_soh_none(self):
        """None SOH should return nominal capacity (fallback)."""
        result = estimate_usable_capacity_ah(soh=None, nominal_ah=100)
        assert result == 100.0

    def test_out_of_bounds_soh_above_1(self):
        """SOH > 1.0 should be clipped to 1.0."""
        result = estimate_usable_capacity_ah(soh=1.5, nominal_ah=100)
        assert result == 100.0

    def test_out_of_bounds_soh_below_0(self):
        """SOH < 0 should be clipped to 0."""
        result = estimate_usable_capacity_ah(soh=-0.5, nominal_ah=100)
        assert result == 0.0


class TestRemainingEnergy:
    """Test energy calculation from SOC and capacity."""

    def test_full_battery_full_voltage(self):
        """Full SOC (1.0), full capacity should give max energy."""
        result = estimate_remaining_energy_wh(
            soc=1.0,
            usable_capacity_ah=100,
            mean_voltage_v=3.7
        )
        assert result == pytest.approx(370.0)  # 1.0 * 100 * 3.7

    def test_half_battery(self):
        """Half SOC (0.5) should give half energy."""
        result = estimate_remaining_energy_wh(
            soc=0.5,
            usable_capacity_ah=100,
            mean_voltage_v=3.7
        )
        assert result == pytest.approx(185.0)  # 0.5 * 100 * 3.7

    def test_empty_battery(self):
        """Empty SOC (0) should give 0 energy."""
        result = estimate_remaining_energy_wh(
            soc=0.0,
            usable_capacity_ah=100,
            mean_voltage_v=3.7
        )
        assert result == 0.0

    def test_invalid_soc_nan(self):
        """NaN SOC should return 0 (conservative)."""
        result = estimate_remaining_energy_wh(
            soc=np.nan,
            usable_capacity_ah=100,
            mean_voltage_v=3.7
        )
        assert result == 0.0

    def test_out_of_bounds_soc_above_1(self):
        """SOC > 1.0 should be clipped to 1.0."""
        result = estimate_remaining_energy_wh(
            soc=1.5,
            usable_capacity_ah=100,
            mean_voltage_v=3.7
        )
        assert result == pytest.approx(370.0)  # Clipped to 1.0

    def test_custom_voltage(self):
        """Custom mean voltage should be used."""
        result = estimate_remaining_energy_wh(
            soc=0.5,
            usable_capacity_ah=50,
            mean_voltage_v=4.0
        )
        assert result == pytest.approx(100.0)  # 0.5 * 50 * 4.0


class TestAutonomy:
    """Test autonomy (time until empty) estimation."""

    def test_normal_autonomy(self):
        """Normal operating case: 140 Wh at 35 W should give ~4 hours."""
        result = estimate_autonomy_h(
            remaining_energy_wh=140,
            predicted_power_w=35
        )
        assert result == pytest.approx(4.0, rel=0.01)

    def test_critical_low_autonomy(self):
        """Low energy, high power should give low autonomy."""
        result = estimate_autonomy_h(
            remaining_energy_wh=30,
            predicted_power_w=35
        )
        assert result == pytest.approx(0.857, rel=0.01)  # < 1 hour

    def test_high_autonomy(self):
        """High energy, low power should give high autonomy."""
        result = estimate_autonomy_h(
            remaining_energy_wh=500,
            predicted_power_w=20
        )
        assert result == pytest.approx(25.0)  # > 24 hours

    def test_zero_energy(self):
        """Zero energy should return 0 autonomy."""
        result = estimate_autonomy_h(
            remaining_energy_wh=0,
            predicted_power_w=35
        )
        assert result == 0.0

    def test_negative_energy_clipped(self):
        """Negative energy should return 0 (clipped)."""
        result = estimate_autonomy_h(
            remaining_energy_wh=-10,
            predicted_power_w=35
        )
        assert result == 0.0

    def test_zero_power_infinite_autonomy(self):
        """Zero power should return 24 hours (avoid division by zero)."""
        result = estimate_autonomy_h(
            remaining_energy_wh=140,
            predicted_power_w=0
        )
        assert result == 24.0

    def test_negative_power_infinite_autonomy(self):
        """Negative power should return 24 hours (conservative)."""
        result = estimate_autonomy_h(
            remaining_energy_wh=140,
            predicted_power_w=-5
        )
        assert result == 24.0


class TestRiskClassification:
    """Test risk state classification."""

    def test_normal_risk(self):
        """Autonomy >= 6 hours should be 'normal'."""
        result = classify_risk(autonomy_h=10.0)
        assert result == "normal"

    def test_advisory_risk(self):
        """Autonomy 2–6 hours should be 'advisory'."""
        result = classify_risk(autonomy_h=4.0)
        assert result == "advisory"

    def test_critical_risk(self):
        """Autonomy < 2 hours should be 'critical'."""
        result = classify_risk(autonomy_h=1.0)
        assert result == "critical"

    def test_offline_risk_negative_autonomy(self):
        """Negative autonomy should be 'offline'."""
        result = classify_risk(autonomy_h=-1.0)
        assert result == "offline"

    def test_offline_risk_nan_autonomy(self):
        """NaN autonomy should be 'offline'."""
        result = classify_risk(autonomy_h=np.nan)
        assert result == "offline"

    def test_offline_risk_none_autonomy(self):
        """None autonomy should be 'offline'."""
        result = classify_risk(autonomy_h=None)
        assert result == "offline"

    def test_low_confidence_override(self):
        """Low confidence (< 0.5) should return 'advisory' regardless of autonomy."""
        result = classify_risk(autonomy_h=20.0, confidence=0.3)
        assert result == "advisory"

    def test_thermal_stress_cold(self):
        """Cold temperature (< 0°C) should add 'advisory'."""
        result = classify_risk(autonomy_h=8.0, temperature_c=-5)
        assert result == "advisory"

    def test_thermal_stress_hot(self):
        """Hot temperature (> 50°C) should add 'advisory'."""
        result = classify_risk(autonomy_h=8.0, temperature_c=55)
        assert result == "advisory"

    def test_normal_temperature_range(self):
        """Normal temperature (5–45°C) should not add 'advisory'."""
        result = classify_risk(autonomy_h=8.0, temperature_c=25)
        assert result == "normal"

    def test_custom_thresholds(self):
        """Custom thresholds should be respected."""
        result = classify_risk(
            autonomy_h=3.0,
            critical_h=5.0,  # Custom
            advisory_h=8.0   # Custom
        )
        assert result == "critical"  # 3 < 5


class TestModeSelection:
    """Test operational mode selection."""

    def test_mode_normal_risk(self):
        """Normal risk should select 'normal' mode."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.select_mode(risk_state="normal")
        assert result == "normal"

    def test_mode_advisory_risk(self):
        """Advisory risk should select 'economy' mode."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.select_mode(risk_state="advisory")
        assert result == "economy"

    def test_mode_critical_risk_night(self):
        """Critical risk at night should select 'sos' mode."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.select_mode(risk_state="critical", hour_of_day=22)
        assert result == "sos"

    def test_mode_critical_risk_day(self):
        """Critical risk during day should select 'off' mode."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.select_mode(risk_state="critical", hour_of_day=14)
        assert result == "off"

    def test_mode_offline_risk(self):
        """Offline risk should select 'off' mode."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.select_mode(risk_state="offline")
        assert result == "off"


class TestIntegration:
    """Integration tests: full risk layer update pipeline."""

    def test_full_update_normal(self):
        """Full update: normal operating conditions."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.update(
            soc=0.80,
            soh=0.95,
            temperature_c=25,
            p_led_w=60,
            hour_of_day=22,
            confidence=0.90,
        )

        assert result["autonomy_h"] > 6  # Should be "normal" autonomy
        assert result["risk_state"] == "normal"
        assert result["mode"] == "normal"
        assert result["c_usable_ah"] == pytest.approx(95.0)

    def test_full_update_advisory(self):
        """Full update: advisory conditions (low reserve)."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.update(
            soc=0.40,
            soh=0.95,
            temperature_c=25,
            p_led_w=60,
            hour_of_day=22,
            confidence=0.90,
        )

        assert 2 < result["autonomy_h"] < 6  # Advisory range
        assert result["risk_state"] == "advisory"
        assert result["mode"] == "economy"

    def test_full_update_critical(self):
        """Full update: critical conditions (imminent failure)."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.update(
            soc=0.05,
            soh=0.95,
            temperature_c=25,
            p_led_w=60,
            hour_of_day=22,
            confidence=0.90,
        )

        assert result["autonomy_h"] < 2  # Critical range
        assert result["risk_state"] == "critical"
        assert result["mode"] == "sos"

    def test_full_update_low_confidence(self):
        """Full update with low confidence: conservative estimate."""
        risk_layer = SmartPoleRiskLayer()
        result_high_conf = risk_layer.update(
            soc=0.80, soh=0.95, temperature_c=25,
            p_led_w=60, hour_of_day=22, confidence=0.95
        )

        result_low_conf = risk_layer.update(
            soc=0.80, soh=0.95, temperature_c=25,
            p_led_w=60, hour_of_day=22, confidence=0.3
        )

        # Low confidence should give lower autonomy estimate
        assert result_low_conf["autonomy_h"] < result_high_conf["autonomy_h"]
        assert result_low_conf["risk_state"] == "advisory"

    def test_full_update_thermal_stress(self):
        """Full update with thermal stress: reduced autonomy."""
        risk_layer = SmartPoleRiskLayer()
        result_normal = risk_layer.update(
            soc=0.60, soh=0.95, temperature_c=25,
            p_led_w=60, hour_of_day=22, confidence=0.95
        )

        result_cold = risk_layer.update(
            soc=0.60, soh=0.95, temperature_c=-5,
            p_led_w=60, hour_of_day=22, confidence=0.95
        )

        # Thermal stress should reduce autonomy
        assert result_cold["autonomy_h"] < result_normal["autonomy_h"]

    def test_full_update_invalid_soc(self):
        """Full update with NaN SOC: fallback to safe estimate."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.update(
            soc=np.nan,
            soh=0.95,
            temperature_c=25,
            p_led_w=60,
            hour_of_day=22,
            confidence=0.95,
        )

        assert result["e_remaining_wh"] == 0.0  # NaN SOC → 0 energy
        assert result["risk_state"] in ["critical", "offline"]  # Very conservative

    def test_full_update_day_time(self):
        """Full update during daytime (should affect night duration)."""
        risk_layer = SmartPoleRiskLayer()
        result_night = risk_layer.update(
            soc=0.40, soh=0.95, temperature_c=25,
            p_led_w=60, hour_of_day=22, confidence=0.95
        )

        result_day = risk_layer.update(
            soc=0.40, soh=0.95, temperature_c=25,
            p_led_w=60, hour_of_day=14, confidence=0.95
        )

        # Daytime should have higher autonomy (less night consumption ahead)
        assert result_day["autonomy_h"] > result_night["autonomy_h"]


class TestEdgeCases:
    """Edge case and stress tests."""

    def test_zero_nominal_capacity(self):
        """Zero nominal capacity should not crash."""
        risk_layer = SmartPoleRiskLayer(capacity_nominal_ah=0)
        result = risk_layer.update(
            soc=1.0, soh=1.0, temperature_c=25,
            p_led_w=60, hour_of_day=22
        )
        assert result["c_usable_ah"] == 0.0

    def test_extreme_power(self):
        """Extreme LED power should not crash."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.update(
            soc=0.5, soh=0.95, temperature_c=25,
            p_led_w=1000,  # Extreme
            hour_of_day=22
        )
        assert isinstance(result["autonomy_h"], float)

    def test_boundary_hour_values(self):
        """Boundary hour values should be handled."""
        risk_layer = SmartPoleRiskLayer()

        for hour in [0, 5, 6, 20, 21, 23]:
            result = risk_layer.update(
                soc=0.5, soh=0.95, temperature_c=25,
                p_led_w=60, hour_of_day=hour
            )
            assert isinstance(result["autonomy_h"], float)
            assert result["autonomy_h"] >= 0

    def test_very_high_soc_soh(self):
        """Very high SOC/SOH should give maximum autonomy."""
        risk_layer = SmartPoleRiskLayer()
        result = risk_layer.update(
            soc=1.0, soh=1.0, temperature_c=25,
            p_led_w=10,  # Low power
            hour_of_day=22
        )
        assert result["autonomy_h"] > 24


class TestClassIntegration:
    """Test the SmartPoleRiskLayer class as a whole."""

    def test_class_initialization(self):
        """Class initialization with custom parameters."""
        risk_layer = SmartPoleRiskLayer(
            capacity_nominal_ah=200,
            v_mean_v=4.0,
            autonomy_critical_h=1.0,
            autonomy_advisory_h=4.0,
        )
        assert risk_layer.capacity_nominal == 200
        assert risk_layer.v_mean == 4.0
        assert risk_layer.critical_threshold == 1.0
        assert risk_layer.advisory_threshold == 4.0

    def test_state_tracking(self):
        """Class should track current state across updates."""
        risk_layer = SmartPoleRiskLayer()

        # First update: normal
        risk_layer.update(soc=0.8, soh=0.95, temperature_c=25, hour_of_day=22)
        assert risk_layer.current_state == "normal"

        # Second update: critical
        risk_layer.update(soc=0.05, soh=0.95, temperature_c=25, hour_of_day=22)
        assert risk_layer.current_state == "critical"

    def test_repr(self):
        """String representation should be informative."""
        risk_layer = SmartPoleRiskLayer()
        repr_str = repr(risk_layer)
        assert "SmartPoleRiskLayer" in repr_str
        assert "100" in repr_str  # Nominal capacity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
