# Template de Retorno -- V8B2 Canonical ESP32

**Preencher e devolver junto com logs e arquivos do validador**

---

## Identificacao

| Campo | Valor |
|-------|-------|
| Placa | (ex: ESP32-DevKitC v4) |
| Chip | (ex: ESP32-D0WD-V3) |
| Flash size | (ex: 4MB) |
| PSRAM | (sim/nao) |
| IDE | (ex: Arduino IDE 2.3, PlatformIO 6.x) |
| Arduino-ESP32 version | (ex: 2.0.14) |
| Firmware file | firmware_soc_v8b2_canonical.ino |
| Firmware version | V8B2 |
| Data de execucao | YYYY-MM-DD |
| Executado por | (nome ou iniciais) |

---

## Modos Executados

- [ ] GOLDEN (20 amostras)
- [ ] EXTENDED (120 amostras)
- [ ] ANOMALY (10 cenarios)

---

## Compilacao

| Item | Resultado |
|------|-----------|
| Compilou sem erros | sim / nao |
| Erros de compilacao | (descrever se houver) |
| Warnings de compilacao | (descrever se houver) |
| Flash utilizado | (ex: 72%) |
| RAM utilizada | (ex: 15%) |

---

## Upload e Inicializacao

| Item | Resultado |
|------|-----------|
| Upload OK | sim / nao |
| Serial abriu (115200) | sim / nao |
| Linhas de header impressas | sim / nao |
| Primeiro dado apareceu | sim / nao |

---

## Execucao

| Item | Valor |
|------|-------|
| Total de linhas de dados impressas | |
| Resets / travamentos durante execucao | 0 / N (descrever) |
| Tempo total de execucao (estimado) | (segundos) |
| Linhas BEGIN/END impressas | sim / nao |
| Linha DONE impressa | sim / nao |

---

## Resultados -- GOLDEN (se rodado)

| Metrica | Valor | Threshold | Status |
|---------|-------|-----------|--------|
| Amostras correspondidas | / 20 | 20/20 | |
| MAE | | < 0.001 | PASS/FAIL |
| RMSE | | < 0.001 | PASS/FAIL |
| R2 | | > 0.99 | PASS/FAIL |
| Max AE | | | |
| Latencia media (ms) | | < 0.5 | |
| Heap livre minimo (bytes) | | > 280000 | |
| Validador executado | sim / nao | | |
| Status validador | PASS / FAIL / N/A | | |

---

## Resultados -- EXTENDED (se rodado)

| Metrica | Valor | Threshold | Status |
|---------|-------|-----------|--------|
| Amostras totais | / 120 | 120 | |
| MAE (nao-saturados) | | < 0.001 | PASS/FAIL |
| RMSE (nao-saturados) | | < 0.001 | PASS/FAIL |
| R2 (nao-saturados) | | > 0.99 | PASS/FAIL |
| Amostras WARN_SAT | / 6 esperadas | 6 | |
| Latencia media (ms) | | < 0.5 | |
| Latencia P95 (ms) | | < 1.0 | |
| Latencia max (ms) | | < 2.0 | |
| Heap livre minimo (bytes) | | > 280000 | |
| Validador executado | sim / nao | | |
| Status validador | PASS / FAIL / N/A | | |

---

## Resultados -- ANOMALY (se rodado)

| Metrica | Valor | Threshold | Status |
|---------|-------|-----------|--------|
| Cenarios executados | / 10 | 10 | |
| True positives | | | |
| False positives | | | |
| False negatives | | | |
| Recall (embutidos) | | >= 0.90 | PASS/FAIL |
| False positive rate | | < 0.10 | |
| Status validador | PASS / FAIL / N/A | | |

---

## Arquivos Devolvidos

- [ ] `v8b2_esp32_golden_log.txt` (log bruto GOLDEN)
- [ ] `v8b2_esp32_extended_log.txt` (log bruto EXTENDED)
- [ ] `v8b2_esp32_anomaly_log.txt` (log bruto ANOMALY)
- [ ] `v8b2_validation_metrics.json`
- [ ] `v8b2_golden_comparison.csv`
- [ ] `v8b2_extended_comparison.csv`
- [ ] `v8b2_anomaly_comparison.csv`
- [ ] `v8b2_validation_report.md`

---

## Observacoes Livres

(descrever qualquer comportamento inesperado, mensagens de erro, latencias altas, etc.)

```
[observacoes aqui]
```

---

## Erro Bruto (se houver)

(colar mensagem de erro completa -- erro bruto e evidencia valida)

```
[erro aqui]
```

---

*Template V8B2 Canonical | Preencher e devolver com todos os arquivos acima*
