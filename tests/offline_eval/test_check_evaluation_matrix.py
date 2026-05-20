from scripts.offline_eval.check_evaluation_matrix import validate_matrix


def row(identifier, metric, split="split temporal"):
    return {
        "evaluation_id": identifier,
        "objeto_avaliado": "SOC",
        "split": split,
        "metrica": metric,
        "objetivo": "objetivo",
        "threshold_inicial": "a definir",
        "obrigatoria_para_claim": "sim",
        "observacoes": "observacao",
    }


def complete_rows():
    rows = [
        row("E1", "MAE", "random_holdout"),
        row("E2", "RMSE", "split temporal"),
        row("E3", "R2", "split por ciclo"),
        row("E4", "max_abs_error", "split por célula"),
        row("E5", "p95_abs_error", "leave-one-cell-out"),
        row("E6", "latency_mean_ms", "replay embarcado"),
        row("E7", "latency_p95_ms", "replay embarcado"),
        row("E8", "heap_min_bytes", "replay embarcado"),
        row("E9", "sample_id_match_rate", "replay embarcado"),
        row("E10", "anomaly_recall", "replay embarcado"),
        row("E11", "anomaly_false_positive_rate", "stream digital V8C"),
    ]
    return rows


def has_fail(messages):
    return any(message.level == "FAIL" for message in messages)


def test_duplicate_ids_fail():
    rows = complete_rows()
    rows[1]["evaluation_id"] = rows[0]["evaluation_id"]
    assert has_fail(validate_matrix(rows))


def test_missing_column_fails():
    rows = complete_rows()
    del rows[0]["observacoes"]
    assert has_fail(validate_matrix(rows))


def test_empty_required_field_fails():
    rows = complete_rows()
    rows[0]["objetivo"] = ""
    assert has_fail(validate_matrix(rows))


def test_missing_required_metric_fails():
    rows = [item for item in complete_rows() if item["metrica"] != "MAE"]
    assert has_fail(validate_matrix(rows))


def test_real_matrix_passes():
    import csv
    from pathlib import Path

    with Path("experiments/registries/evaluation_matrix.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert not has_fail(validate_matrix(rows))
