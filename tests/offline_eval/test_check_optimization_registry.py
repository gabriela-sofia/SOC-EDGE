from scripts.offline_eval.check_optimization_registry import validate_registry


SCHEMA = [
    {"field": "optimization_id", "required": "true", "allowed_values": ""},
    {"field": "frente", "required": "true", "allowed_values": "target físico|features|splits|modelos|híbridos|quantização|anomalias|drift|SOH|embarcado"},
    {"field": "nome", "required": "true", "allowed_values": ""},
    {"field": "objetivo", "required": "true", "allowed_values": ""},
    {"field": "tipo", "required": "true", "allowed_values": ""},
    {"field": "status", "required": "true", "allowed_values": "consolidado|parcial|planejado|candidato"},
    {"field": "entrada_esperada", "required": "true", "allowed_values": ""},
    {"field": "saida_esperada", "required": "true", "allowed_values": ""},
    {"field": "compativel_esp32", "required": "true", "allowed_values": "sim|não|parcial|indireto/offline|planejado"},
    {"field": "custo_embarcado_estimado", "required": "true", "allowed_values": "nenhum|baixo|médio|alto"},
    {"field": "depende_de_dados_locais", "required": "true", "allowed_values": "sim|não"},
    {"field": "claim_permitido", "required": "true", "allowed_values": ""},
    {"field": "claim_proibido", "required": "true", "allowed_values": ""},
    {"field": "proxima_fase", "required": "true", "allowed_values": ""},
]


def row(identifier, frente):
    return {
        "optimization_id": identifier,
        "frente": frente,
        "nome": "item",
        "objetivo": "objetivo",
        "tipo": "feature",
        "status": "planejado",
        "entrada_esperada": "entrada",
        "saida_esperada": "saida",
        "compativel_esp32": "sim",
        "custo_embarcado_estimado": "baixo",
        "depende_de_dados_locais": "não",
        "claim_permitido": "claim permitido",
        "claim_proibido": "claim proibido",
        "proxima_fase": "fase",
    }


def complete_rows():
    fronts = ["target físico", "features", "splits", "modelos", "híbridos", "quantização", "anomalias", "drift", "SOH", "embarcado"]
    return [row(f"ID_{index}", frente) for index, frente in enumerate(fronts)]


def has_fail(messages):
    return any(message.level == "FAIL" for message in messages)


def test_duplicate_ids_fail():
    rows = complete_rows()
    rows[1]["optimization_id"] = rows[0]["optimization_id"]
    assert has_fail(validate_registry(rows, SCHEMA))


def test_missing_column_fails():
    rows = complete_rows()
    del rows[0]["claim_proibido"]
    assert has_fail(validate_registry(rows, SCHEMA))


def test_empty_required_field_fails():
    rows = complete_rows()
    rows[0]["nome"] = ""
    assert has_fail(validate_registry(rows, SCHEMA))


def test_missing_required_front_fails():
    rows = [row("ID_ONLY", "features")]
    assert has_fail(validate_registry(rows, SCHEMA))


def test_real_registry_passes():
    import csv
    from pathlib import Path

    with Path("experiments/registries/optimization_registry.csv").open(encoding="utf-8", newline="") as handle:
        registry_rows = list(csv.DictReader(handle))
    with Path("experiments/schemas/optimization_registry_schema.csv").open(encoding="utf-8", newline="") as handle:
        schema_rows = list(csv.DictReader(handle))
    assert not has_fail(validate_registry(registry_rows, schema_rows))
