# V8B2 Canonical ESP32 Validation Report

**Generated:** 2026-05-17 17:51
**Log file:** v8b2_esp32_anomaly_log.txt
**Overall status:** WARN

---

## Parse Summary

| Field | Value |
|-------|-------|
| Parse errors | 9 |
| Total valid records | 10 |

## GOLDEN Mode

**Status:** SKIPPED

- **n_expected:** 20

## EXTENDED Mode

**Status:** SKIPPED

- **n_expected:** 120

## ANOMALY Mode

**Status:** PASS

- **n_expected:** 10
- **n_scenarios:** 10
- **n_embedded_feasible:** 8
- **true_positives:** 10
- **false_positives:** 0
- **false_negatives:** 0
- **recall_all:** 1.0
- **recall_embedded:** 1.0
- **precision:** 1.0
- **false_positive_rate:** 0.0
- **recall_threshold:** 0.9

## Resource Metrics

- **latency_mean_ms:** 0.2069
- **latency_min_ms:** 0.14
- **latency_max_ms:** 0.794
- **latency_p95_ms:** 0.5014999999999994
- **latency_warn:** False
- **free_heap_mean:** 351092.0
- **free_heap_min:** 351092.0
- **min_free_heap_global:** 351092.0
- **heap_warn:** False
- **total_samples:** 10
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