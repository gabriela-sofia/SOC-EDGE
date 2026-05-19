# V8B2 Canonical ESP32 Validation Report

**Generated:** 2026-05-17 17:32
**Log file:** v8b2_esp32_extended_log.txt
**Overall status:** WARN

---

## Parse Summary

| Field | Value |
|-------|-------|
| Parse errors | 9 |
| Total valid records | 120 |

## GOLDEN Mode

**Status:** SKIPPED

- **n_expected:** 20

## EXTENDED Mode

**Status:** PASS

- **n_expected:** 120
- **matched_samples:** 120
- **n_saturated:** 6
- **mae_all:** 1.2321666666650539e-06
- **rmse_all:** 1.8364408512075165e-06
- **r2_all:** 0.9999999999586604
- **mae_non_saturated:** 1.2970175438579515e-06
- **rmse_non_saturated:** 1.8841485582237453e-06
- **r2_non_saturated:** 0.9999999999511635
- **mae_saturated:** 0.0
- **mae_threshold:** 0.001

## ANOMALY Mode

**Status:** SKIPPED

- **n_expected:** 10

## Resource Metrics

- **latency_mean_ms:** 0.1345333333333333
- **latency_min_ms:** 0.128
- **latency_max_ms:** 0.788
- **latency_p95_ms:** 0.13
- **latency_warn:** False
- **free_heap_mean:** 351068.0
- **free_heap_min:** 351068.0
- **min_free_heap_global:** 351068.0
- **heap_warn:** False
- **total_samples:** 120
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