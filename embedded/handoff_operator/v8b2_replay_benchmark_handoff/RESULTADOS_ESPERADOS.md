# Resultados Esperados — V8B2 Replay Benchmark

## Resumo

Ao executar os três replays (GOLDEN, EXTENDED, ANOMALY) no ESP32, você deverá obter métricas de latência, consumo de heap, comportamento de anomalias e estabilidade. Este documento detalha o que é esperado e aceitável.

---

## Replays e Modos

### GOLDEN (Validação Curta)

- **Propósito:** Confirmação rápida de paridade do modelo.
- **Duração:** ~5 segundos.
- **Total de registros esperado:** 20.
- **Modo esperado:** `GOLDEN`.
- **Parse errors:** 0.
- **Status esperado:** OK para 100% dos registros.
- **Anomalias:** 0 (este é um replay limpo sem cenários de anomalia).
- **Heap esperado:** Mínimo > 100 KB durante execução.
- **Resets:** 0 esperados.

**Métricas latência esperadas:**
| Métrica | Esperado | Aceitável |
|---------|----------|-----------|
| Latência média | 0.16 ms | até 0.3 ms |
| Latência p95 | 0.17 ms | até 0.5 ms |
| Latência p99 | 0.20 ms | até 0.7 ms |
| Latência máx | 0.30 ms | até 1.0 ms |

### EXTENDED (Validação Média)

- **Propósito:** Teste de estabilidade e variação de latência em replay maior.
- **Duração:** ~10 segundos.
- **Total de registros esperado:** 120.
- **Modo esperado:** `EXTENDED`.
- **Parse errors:** 0.
- **Status esperado:** OK para 100% dos registros.
- **Anomalias:** 0 (este é um replay limpo).
- **Heap esperado:** Mínimo > 100 KB; variação < 10 KB entre amostras.
- **Resets:** 0 esperados.

**Métricas latência esperadas:**
| Métrica | Esperado | Aceitável |
|---------|----------|-----------|
| Latência média | 0.13 ms | até 0.3 ms |
| Latência p95 | 0.13 ms | até 0.5 ms |
| Latência p99 | 0.15 ms | até 0.7 ms |
| Latência máx | 0.50 ms | até 1.5 ms |

### ANOMALY (Cenários Controlados)

- **Propósito:** Validar detecção de anomalias em condições pré-injetadas.
- **Duração:** ~3 segundos.
- **Total de registros esperado:** 10.
- **Modo esperado:** `ANOMALY`.
- **Parse errors:** 0.
- **Status esperado:** OK para todos (detecção não fail o processamento).
- **Anomalias detectadas:** 10/10 (100% das amostras injetadas devem ter flag).
- **Anomaly codes esperados:** Conforme `anomaly/anomaly_manifest_v8b2.csv`.
- **Heap esperado:** Similar ao EXTENDED.
- **Resets:** 0 esperados.

**Métricas latência esperadas:**
| Métrica | Esperado | Aceitável |
|---------|----------|-----------|
| Latência média | 0.21 ms | até 0.4 ms |
| Latência p95 | 0.50 ms | até 1.0 ms |
| Latência p99 | 0.70 ms | até 1.5 ms |
| Latência máx | 1.00 ms | até 2.0 ms |

---

## Métricas Capturadas

Ao processar os logs com `scripts/validate_returned_logs.py`, você receberá:

### Contagem e Validação
- `total_records` — Total de linhas parseadas nos 3 logs.
- `parse_errors` — Número de linhas que não matcham o schema.
- `status_ok_rate` — Percentual de status=OK (esperado: 1.0).

### Latência (inferência)
- `latency_mean_ms` — Latência média em milissegundos.
- `latency_p95_ms` — Percentil 95.
- `latency_p99_ms` — Percentil 99 (se calculado).
- `latency_max_ms` — Máxima.

### Heap
- `free_heap_min_bytes` — Mínimo de heap livre visto durante execução.
- `min_free_heap_min_bytes` — Estatística dupla (se sistema reporta dois valores de heap).
- `max_alloc_heap_min_bytes` — Maior alocação consecutiva vista.

### Comportamento
- `anomaly_rate` — Percentual de registros com flag de anomalia.
  - GOLDEN/EXTENDED: 0.0.
  - ANOMALY: 1.0.
- `duplicate_sample_id_count` — Linhas com ID duplicado (esperado: 0).
- `resets_observados` — Número de resets/crashes durante execução (esperado: 0).

### Ambiente
- `flash_usado_bytes` — Reportado ao compilar.
- `ambiente_usado` — Arduino IDE / PlatformIO / ESP-IDF.

---

## Critérios de Aceite

### PASS

✓ `parse_errors == 0`  
✓ `status_ok_rate == 1.0`  
✓ `resets_observados == 0`  
✓ Latência mean < 0.5 ms (recomendado) ou < 1.0 ms (aceitável).  
✓ Heap min > 100 KB.  
✓ Anomalias detectadas 100% em ANOMALY.  
✓ Nenhuma linha corrompida na serial.  
✓ Todos os 3 replays completados com sucesso.  

### FAIL

✗ `parse_errors > 0` → Formato de serial quebrado ou baud rate errado.  
✗ `status_ok_rate < 1.0` → Lógica de modelo ou escrita serial inconsistente.  
✗ `resets_observados > 0` → Problema de memória ou instabilidade.  
✗ Heap < 50 KB → Risco de estouro de pilha.  
✗ Latência > 5 ms consecutivo → Problema de performance ou scheduler.  
✗ Falta algum dos 3 replays.  
✗ Anomaly rate < 0.8 em ANOMALY → Lógica de detecção não funcionando.  

---

## Variação Esperada por Ambiente

Os valores acima são **baselines** obtidos em laboratório. Você pode observar pequenas variações:

| Fator | Causa | Tolerância |
|-------|-------|-----------|
| Latência | Clock, compilador, otimização | ±30% é normal |
| Heap | Fragmentação, libertador | ±5% é normal |
| Resets | Estabilidade USB | 0 esperado; 1 é suspeito |
| Parse errors | Ruído serial, baud rate | 0 esperado; > 5 é problema |

---

## Interpretação de Anomalias

O campo `anomaly_flag` pode ser:
- `0` — Sem detecção.
- `1` (ou ID específico) — Anomalia detectada.

Em ANOMALY, esperamos:
- Modo ANOMALY → 100% com flag.
- Anomaly code ∈ {1, 2, 3, ...} conforme manifest.

Se anomalias não forem detectadas, verifique:
1. Arquivo `anomaly_manifest_v8b2.csv` foi carregado?
2. Thresholds de detecção estão corretos?
3. Dados injetados estão no campo esperado?

Consulte `anomaly/anomaly_manifest_v8b2.csv` para detalhe de cada código.

---

## Exemplo de Retorno Bem-Sucedido

```json
{
  "total_records": 150,
  "parse_errors": 0,
  "status_ok_rate": 1.0,
  "latency_mean_ms": 0.143293,
  "latency_p95_ms": 0.141550,
  "latency_p99_ms": 0.160000,
  "latency_max_ms": 0.501500,
  "free_heap_min_bytes": 351068,
  "min_free_heap_min_bytes": null,
  "max_alloc_heap_min_bytes": null,
  "anomaly_rate": 0.067,
  "duplicate_sample_id_count": 0,
  "resets_observados": 0,
  "ambiente_usado": "Arduino IDE",
  "flash_usado_bytes": 262144,
  "modo_breakdown": {
    "GOLDEN": { "n": 20, "lat_mean": 0.164, "heap_min": 351068 },
    "EXTENDED": { "n": 120, "lat_mean": 0.135, "heap_min": 351068 },
    "ANOMALY": { "n": 10, "lat_mean": 0.207, "heap_min": 351092, "anomaly_rate": 1.0 }
  }
}
```

---

## Se Algo Sair Fora do Esperado

| Sintoma | Causa Provável | Ação |
|---------|----------------|------|
| parse_errors > 0 | Serial corrompida ou baud rate errado | Consulte TROUBLESHOOTING.md |
| Latência > 2 ms | Otimizações desligadas ou placa sobrecarregada | Verificar IDE settings |
| Heap < 100 KB | Stack underflow ou leak | Resetar e revisar fragmentação |
| Resets durante execução | Watchdog timer ou overflow | Aumentar stack ou verificar power |
| Sem anomalias em ANOMALY | Thresholds ou injeção incorretos | Revisar anomaly_manifest_v8b2.csv |

Anote qualquer anomalia em `observacoes_operador_template.md` e entregue mesmo assim para diagnóstico.

---

**Versão:** V8B2  
**Data:** 2026-05-19
