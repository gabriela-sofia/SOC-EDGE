import pytest

from scripts.parse_v8b2_benchmark import (
    compute_global_metrics,
    compute_mode_metrics,
    main,
    parse_log_lines,
    percentile,
)


def test_valid_line_is_parsed():
    records, errors = parse_log_lines(
        ["0,GOLDEN,0.208489,0.790,351068,351068,114676,0,0,PASS"]
    )
    assert not errors
    assert len(records) == 1
    assert records[0].sample_id == 0
    assert records[0].mode == "GOLDEN"
    assert records[0].inference_time_ms == pytest.approx(0.790)
    assert records[0].free_heap == 351068


def test_serial_noise_is_ignored_and_malformed_record_is_reported():
    records, errors = parse_log_lines(
        [
            "ets Jul 29 2019 12:21:46",
            "// Schema: sample_id,mode,...",
            "1,GOLDEN,not-a-number,0.100,351068,351068,114676,0,0,PASS",
        ]
    )
    assert records == []
    assert len(errors) == 1
    assert "could not convert" in errors[0].reason


def test_mode_metrics_latency_and_duplicate_sample_ids():
    lines = [
        "0,GOLDEN,0.2,0.100,1000,900,800,0,0,PASS",
        "1,GOLDEN,0.3,0.200,990,890,790,0,0,PASS",
        "1,GOLDEN,0.4,0.300,980,880,780,0,0,PASS",
    ]
    records, errors = parse_log_lines(lines)
    metrics = compute_mode_metrics(records, errors)
    golden = metrics["GOLDEN"]
    assert golden["n_records"] == 3
    assert golden["latency_mean_ms"] == pytest.approx(0.2)
    assert golden["latency_p95_ms"] == pytest.approx(percentile([0.1, 0.2, 0.3], 0.95))
    assert golden["duplicate_sample_id_count"] == 1


def test_modes_are_separated_and_global_metrics_work():
    records, errors = parse_log_lines(
        [
            "0,GOLDEN,0.2,0.100,1000,900,800,0,0,PASS",
            "0,EXTENDED,0.2,0.200,990,890,790,0,0,PASS",
            "0,ANOMALY,0.2,0.300,980,880,780,1,7,ANOMALY",
        ]
    )
    mode_metrics = compute_mode_metrics(records, errors)
    global_metrics = compute_global_metrics(records, errors)
    assert mode_metrics["GOLDEN"]["n_records"] == 1
    assert mode_metrics["EXTENDED"]["n_records"] == 1
    assert mode_metrics["ANOMALY"]["anomaly_flag_count"] == 1
    assert global_metrics["total_records"] == 3
    assert global_metrics["modes_seen"] == ["ANOMALY", "EXTENDED", "GOLDEN"]
    assert global_metrics["overall_status_ok_rate"] == pytest.approx(1.0)


def test_warn_status_counts_as_noncritical_status():
    records, errors = parse_log_lines(
        ["9,EXTENDED,1.0,0.100,1000,900,800,0,0,WARN_SAT"]
    )
    metrics = compute_mode_metrics(records, errors)
    assert metrics["EXTENDED"]["n_status_ok"] == 1
    assert metrics["EXTENDED"]["n_status_fail"] == 0


def test_main_fails_without_valid_records(tmp_path, capsys):
    log_path = tmp_path / "noise.txt"
    log_path.write_text("boot noise\n// comment\n", encoding="utf-8")
    exit_code = main([str(log_path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No valid V8B2 benchmark records found." in captured.err
