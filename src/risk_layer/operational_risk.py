"""
Smart Pole Operational Risk Layer — EXPERIMENTAL PROTOTYPE

A lightweight, rule-based decision module for estimating battery autonomy and
operational risk in IoT smart pole systems.

⚠️ STATUS: PROTOTYPE ONLY
- Thresholds (2h critical, 6h advisory) are PLACEHOLDERS
- NOT field-validated; requires Phase 3C calibration
- Assumes SOC and SOH inputs are pre-computed and correct
- Does NOT validate input quality; focuses on operational decision logic
- Autonomy estimates are heuristic-based; require real pole data for validation

Inputs: SOC, SOH, temperature, current, LED power, hour of day, confidence
Outputs: autonomy hours (placeholder units), risk state, operational mode

Author: SOC Project Team
Date: 2026-05-07
Reference: REPORTS/29_SMART_POLE_OPERATIONAL_RISK_LAYER_SPEC.md (Section 14: Limitations & Caveats)

NOT FOR PRODUCTION USE until Phase 3C field validation is complete.
"""

import numpy as np
from typing import Dict, Tuple, Optional


class SmartPoleRiskLayer:
    """
    Lightweight risk layer for smart pole battery autonomy and state management.

    ⚠️ EXPERIMENTAL: Thresholds are PLACEHOLDERS and require field calibration.
    Use autonomy_critical_h and autonomy_advisory_h as editable parameters.

    This class consumes pre-computed SOC/SOH estimates and does NOT validate them.
    Autonomy estimates are heuristic-based; real performance depends on:
    - Actual pole consumption profile (LED + baseline power)
    - Solar charging contribution (not explicitly modeled)
    - Battery voltage degradation over cycles
    - Temperature effects on capacity and discharge rate

    Parameters:
    -----------
    capacity_nominal_ah : float
        Nominal battery capacity in Ah (e.g., 100)
    v_mean_v : float
        Mean discharge voltage in V (e.g., 3.7 for Li-ion)
    autonomy_critical_h : float
        PLACEHOLDER threshold for "critical" state (hours, default 2.0).
        Requires field calibration; do NOT treat as production value.
    autonomy_advisory_h : float
        PLACEHOLDER threshold for "advisory" state (hours, default 6.0).
        Requires field calibration; do NOT treat as production value.
    confidence_threshold : float
        Confidence threshold below which to use conservative estimates (default 0.5)
    """

    def __init__(
        self,
        capacity_nominal_ah: float = 100.0,
        v_mean_v: float = 3.7,
        autonomy_critical_h: float = 2.0,
        autonomy_advisory_h: float = 6.0,
        confidence_threshold: float = 0.5,
    ):
        self.capacity_nominal = capacity_nominal_ah
        self.v_mean = v_mean_v
        self.critical_threshold = autonomy_critical_h
        self.advisory_threshold = autonomy_advisory_h
        self.confidence_threshold = confidence_threshold

        # For hysteresis (optional)
        self.current_state = "normal"
        self.last_autonomy = 24.0

        # Configuration: thresholds (editable)
        self.state_config = {
            "normal_to_advisory_down": 5.5,  # Hysteresis margin
            "advisory_to_critical_down": 1.5,
            "critical_to_advisory_up": 2.5,
            "advisory_to_normal_up": 6.5,
        }

    def estimate_usable_capacity_ah(self, soh: float) -> float:
        """
        Estimate usable battery capacity given state of health.

        Parameters:
        -----------
        soh : float
            State of health, [0, 1] where 1 = new, 0.8 = EOL

        Returns:
        --------
        float : Usable capacity in Ah

        Formula: C_usable = SOH * C_nominal
        """
        if soh is None or np.isnan(soh):
            return self.capacity_nominal  # Optimistic fallback

        soh = np.clip(soh, 0, 1)  # Bound to valid range
        return soh * self.capacity_nominal

    def estimate_remaining_energy_wh(
        self,
        soc: float,
        usable_capacity_ah: float,
        mean_voltage_v: Optional[float] = None
    ) -> float:
        """
        Estimate remaining energy given SOC and usable capacity.

        Parameters:
        -----------
        soc : float
            State of charge, [0, 1]
        usable_capacity_ah : float
            Usable capacity in Ah
        mean_voltage_v : float, optional
            Mean voltage (V). If None, uses default (3.7 V)

        Returns:
        --------
        float : Remaining energy in Wh

        Formula: E_remaining = SOC * C_usable * V_mean
        """
        if soc is None or np.isnan(soc):
            return 0.0  # Conservative fallback

        soc = np.clip(soc, 0, 1)  # Bound to valid range
        v_mean = mean_voltage_v if mean_voltage_v is not None else self.v_mean

        return soc * usable_capacity_ah * v_mean

    def estimate_autonomy_h(
        self,
        remaining_energy_wh: float,
        predicted_power_w: float
    ) -> float:
        """
        Estimate autonomy (hours until empty) given remaining energy and power.

        Parameters:
        -----------
        remaining_energy_wh : float
            Remaining energy in Wh
        predicted_power_w : float
            Predicted average power draw in W

        Returns:
        --------
        float : Autonomy in hours

        Formula: Autonomy = E_remaining / P_avg

        Notes:
        - If P_avg <= 0, returns 24 hours (infinite autonomy estimate)
        - If E_remaining <= 0, returns 0 hours
        """
        if remaining_energy_wh <= 0:
            return 0.0

        if predicted_power_w <= 0:
            return 24.0  # Avoid division by zero; assume infinite

        autonomy = remaining_energy_wh / predicted_power_w
        return max(0.0, autonomy)  # Ensure non-negative

    def classify_risk(
        self,
        autonomy_h: float,
        temperature_c: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> str:
        """
        Classify operational risk state based on autonomy and optional conditions.

        Parameters:
        -----------
        autonomy_h : float
            Estimated autonomy in hours
        temperature_c : float, optional
            Current temperature in °C
        confidence : float, optional
            SOC/SOH confidence, [0, 1]

        Returns:
        --------
        str : Risk state in ["normal", "advisory", "critical", "offline"]

        Rules:
        - OFFLINE: Invalid input or NaN autonomy
        - ADVISORY: Low confidence or thermal stress
        - CRITICAL: autonomy < 2 hours
        - ADVISORY: autonomy < 6 hours
        - NORMAL: autonomy >= 6 hours
        """
        # Handle invalid/missing inputs
        if autonomy_h is None or np.isnan(autonomy_h) or autonomy_h < 0:
            return "offline"

        # Confidence check
        if confidence is not None and confidence < self.confidence_threshold:
            return "advisory"

        # Thermal stress check
        if temperature_c is not None:
            if temperature_c < 0 or temperature_c > 50:
                return "advisory"

        # Primary classification: autonomy
        if autonomy_h < self.critical_threshold:
            return "critical"
        elif autonomy_h < self.advisory_threshold:
            return "advisory"
        else:
            return "normal"

    def select_mode(
        self,
        risk_state: str,
        hour_of_day: Optional[int] = None
    ) -> str:
        """
        Select operational mode based on risk state and time of day.

        Parameters:
        -----------
        risk_state : str
            Risk state from classify_risk()
        hour_of_day : int, optional
            Hour of day [0–23] for day/night detection

        Returns:
        --------
        str : Operational mode in ["normal", "economy", "sos", "off"]

        Mode Definitions:
        - NORMAL: 100% LED brightness; full operation
        - ECONOMY: 60% LED brightness; extend autonomy
        - SOS: 20% LED brightness; minimum survival until dawn
        - OFF: 0% LED brightness; no operation
        """
        if risk_state == "normal":
            return "normal"
        elif risk_state == "advisory":
            return "economy"
        elif risk_state == "critical":
            if self._is_night(hour_of_day):
                return "sos"
            else:
                return "off"
        else:  # offline
            return "off"

    def update(
        self,
        soc: float,
        soh: float,
        temperature_c: float,
        current_a: Optional[float] = None,
        p_led_w: float = 60.0,
        hour_of_day: Optional[int] = None,
        confidence: float = 1.0,
        p_baseline_w: float = 5.0,
    ) -> Dict:
        """
        Complete risk layer update: compute autonomy, classify risk, select mode.

        Parameters:
        -----------
        soc : float
            State of charge [0, 1]
        soh : float
            State of health [0, 1]
        temperature_c : float
            Current temperature in °C
        current_a : float, optional
            Discharge current in A (optional; not used in simple model)
        p_led_w : float
            LED power in W (default 60)
        hour_of_day : int, optional
            Hour [0–23]
        confidence : float
            Confidence in SOC estimate [0, 1]
        p_baseline_w : float
            Baseline controller power in W (default 5)

        Returns:
        --------
        dict : {
            'autonomy_h': float,
            'risk_state': str,
            'mode': str,
            'c_usable_ah': float,
            'e_remaining_wh': float,
            'p_avg_w': float,
        }
        """
        # Usable capacity
        c_usable = self.estimate_usable_capacity_ah(soh)

        # Remaining energy
        e_remaining = self.estimate_remaining_energy_wh(soc, c_usable)

        # Predicted power (simple heuristic)
        t_night = self._estimate_night_duration(hour_of_day)
        p_avg = (p_led_w * t_night + p_baseline_w * (24 - t_night)) / 24.0

        # Autonomy
        autonomy_h = self.estimate_autonomy_h(e_remaining, p_avg)

        # Confidence-based conservative adjustment
        if confidence < self.confidence_threshold or soc is None or soh is None:
            autonomy_h *= 0.8  # Reduce by 20% margin

        # Thermal stress adjustment
        if temperature_c is not None and (temperature_c < 5 or temperature_c > 45):
            autonomy_h *= 0.9  # Reduce by additional 10%

        # Risk classification
        risk_state = self.classify_risk(autonomy_h, temperature_c, confidence)

        # Mode selection
        mode = self.select_mode(risk_state, hour_of_day)

        # Update state
        self.current_state = risk_state
        self.last_autonomy = autonomy_h

        return {
            "autonomy_h": autonomy_h,
            "risk_state": risk_state,
            "mode": mode,
            "c_usable_ah": c_usable,
            "e_remaining_wh": e_remaining,
            "p_avg_w": p_avg,
        }

    # ========== Helper Methods ==========

    def _estimate_night_duration(self, hour_of_day: Optional[int]) -> float:
        """
        Estimate night duration (hours) based on time of day.

        Simplified: assumes 14 hours night in winter, 10 in summer.
        Returns 0 during daytime (5–21 h).

        Parameters:
        -----------
        hour_of_day : int, optional
            Hour [0–23]

        Returns:
        --------
        float : Estimated night hours remaining
        """
        if hour_of_day is None:
            return 14.0  # Conservative default

        if hour_of_day >= 21 or hour_of_day < 5:
            # Night: full 14 hours ahead
            return 14.0
        elif hour_of_day >= 5 and hour_of_day < 8:
            # Dawn: hours until 8 AM
            return 8 - hour_of_day
        else:
            # Day (8–21): no night ahead
            return 0.0

    def _is_night(self, hour_of_day: Optional[int]) -> bool:
        """
        Check if current hour is night (for SOS mode logic).

        Simple heuristic: night = 20:00 to 06:00.
        """
        if hour_of_day is None:
            return True  # Assume night if unknown (conservative)

        return hour_of_day >= 20 or hour_of_day < 6

    def __repr__(self) -> str:
        return (
            f"SmartPoleRiskLayer("
            f"capacity={self.capacity_nominal} Ah, "
            f"v_mean={self.v_mean} V, "
            f"critical_h={self.critical_threshold}, "
            f"advisory_h={self.advisory_threshold})"
        )


# ========== Convenience Functions ==========

def estimate_usable_capacity_ah(soh: float, nominal_ah: float = 100.0) -> float:
    """Pure function version of capacity estimation."""
    if soh is None or np.isnan(soh):
        return nominal_ah
    return np.clip(soh, 0, 1) * nominal_ah


def estimate_remaining_energy_wh(
    soc: float,
    usable_capacity_ah: float,
    mean_voltage_v: float = 3.7
) -> float:
    """Pure function version of energy estimation."""
    if soc is None or np.isnan(soc):
        return 0.0
    return np.clip(soc, 0, 1) * usable_capacity_ah * mean_voltage_v


def estimate_autonomy_h(
    remaining_energy_wh: float,
    predicted_power_w: float
) -> float:
    """Pure function version of autonomy estimation."""
    if remaining_energy_wh <= 0:
        return 0.0
    if predicted_power_w <= 0:
        return 24.0  # Avoid division by zero
    return max(0.0, remaining_energy_wh / predicted_power_w)


def classify_risk(
    autonomy_h: float,
    temperature_c: Optional[float] = None,
    confidence: Optional[float] = None,
    critical_h: float = 2.0,
    advisory_h: float = 6.0,
    confidence_threshold: float = 0.5,
) -> str:
    """Pure function version of risk classification."""
    if autonomy_h is None or np.isnan(autonomy_h) or autonomy_h < 0:
        return "offline"
    if confidence is not None and confidence < confidence_threshold:
        return "advisory"
    if temperature_c is not None and (temperature_c < 0 or temperature_c > 50):
        return "advisory"
    if autonomy_h < critical_h:
        return "critical"
    elif autonomy_h < advisory_h:
        return "advisory"
    else:
        return "normal"


if __name__ == "__main__":
    # Example usage
    risk_layer = SmartPoleRiskLayer(
        capacity_nominal_ah=100,
        v_mean_v=3.7,
        autonomy_critical_h=2.0,
        autonomy_advisory_h=6.0,
    )

    result = risk_layer.update(
        soc=0.40,
        soh=0.95,
        temperature_c=25,
        p_led_w=60,
        hour_of_day=22,
        confidence=0.85,
    )

    print("Risk Layer Output:")
    for key, value in result.items():
        print(f"  {key}: {value}")
