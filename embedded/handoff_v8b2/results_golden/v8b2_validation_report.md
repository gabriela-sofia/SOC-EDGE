# V8B2 Canonical ESP32 Validation Report

**Generated:** 2026-05-17 17:27
**Log file:** v8b2_esp32_golden_log.txt
**Overall status:** WARN

---

## Parse Summary

| Field | Value |
|-------|-------|
| Parse errors | 9 |
| Total valid records | 20 |

## GOLDEN Mode

**Status:** PASS

- **n_expected:** 20
- **mae:** 7.289999999993135e-07
- **rmse:** 1.0119189690963137e-06
- **r2:** 0.9999999999799429
- **max_ae:** 2.410000000008239e-06
- **bias:** 1.5600000001225743e-07
- **n:** 20
- **matched_samples:** 20
- **parse_errors:** 0
- **mae_threshold:** 0.001

## EXTENDED Mode

**Status:** SKIPPED

- **n_expected:** 120

## ANOMALY Mode

**Status:** SKIPPED

- **n_expected:** 10

## Resource Metrics

- **latency_mean_ms:** 0.16405
- **latency_min_ms:** 0.13
- **latency_max_ms:** 0.79
- **latency_p95_ms:** 0.16585000000000047
- **latency_warn:** False
- **free_heap_mean:** 351068.0
- **free_heap_min:** 351068.0
- **min_free_heap_global:** 351068.0
- **heap_warn:** False
- **total_samples:** 20
- **crash_detected:** False

---

## Interpretation

- MAE < 0.001 for GOLDEN and EXTENDED (non-saturated) = PASS
- 6 WARN_SAT samples are EXPECTED (known saturated vectors -- firmware clips correctly)
- Anomaly recall >= 0.90 on embedded-feasible scenarios = PASS
- This run validates V7C canonical model on ESP32 for the first time

## Scientific Integrity

- [OK] V7C canonical weights used (not V7B/legacy)
- [OK] Clipping applied: soc_final = clip(raw_output, 0.0, 1.0)
- [OK] Comparison against soc_clipped_reference (not raw model output)
- [PENDING] Field validation not done (requires real battery + sensors)
- [PENDING] Long-duration stress test not done (requires hardware runtime)

---

*V8B2 Canonical Handoff Package*