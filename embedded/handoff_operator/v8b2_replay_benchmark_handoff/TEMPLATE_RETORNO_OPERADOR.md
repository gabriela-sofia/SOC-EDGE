# Template de Retorno Operacional — V8B2

**Instruções:** Preencha este documento com suas observações e dados de execução. Salve em: `retorno_v8b2_esp32/resultados_execucao.md`

---

## 1. Identificação

- **Operador:** 
- **Data de execução:** 
- **Hora início:** 
- **Hora fim:** 

---

## 2. Hardware e Ambiente

### Placa ESP32

- **Modelo exato:** (ex: ESP32-WROOM-32, DevKit V1)
- **Chip:** ESP32 (silício)
- **Revisão do chip:** 
- **Frequência configurada:** (ex: 80 MHz, 160 MHz, 240 MHz)
- **Flash size:** (ex: 4 MB, 8 MB, 16 MB)
- **Flash tipo:** (ex: SPI)
- **PSRAM:** Sim / Não
- **PSRAM size (se sim):** 

### Ambiente de Desenvolvimento

- **Sistema operacional host:** Windows / macOS / Linux
- **IDE utilizada:** Arduino IDE / PlatformIO / ESP-IDF
- **Versão da IDE:** 
- **Versão do core ESP32:** (ex: 2.0.8, 3.0.0)
- **URL/package do core:** 

### Bibliotecas Relevantes

- Listar qualquer biblioteca customizada ou modificada:
  - 
  - 

---

## 3. Firmware

- **Arquivo firmware:** `firmware/firmware_soc_v8b2_canonical.ino`
- **Versão canônica:** V8B2
- **Header de pesos:** `include/canonical_model_weights_v8b2.h`
- **Header de vetores:** `include/replay_vectors_v8b2.h`
- **Commit do repositório (se aplicável):** 
- **Alterações locais feitas no firmware:** (descreva qualquer mudança)
  - Nenhuma / Descreva:
- **Compilação:** ☐ Sem erro ☐ Com warnings ☐ Falhou
- **Flash usado (reportado ao compilar):** _______ bytes
- **RAM dinâmica (reported by compiler):** _______ bytes
- **Observações de compilação:** 

---

## 4. Execução GOLDEN

| Métrica | Valor | Status |
|---------|-------|--------|
| Logs salvos em | `logs/v8b2_esp32_golden_log.txt` | ☐ Sim ☐ Não |
| Total de records | | |
| Parse errors | | ☐ 0 ☐ > 0 |
| Status OK rate | | ☐ 1.0 ☐ < 1.0 |
| Latência média (ms) | | |
| Latência p95 (ms) | | |
| Latência p99 (ms) | | |
| Latência máxima (ms) | | |
| Heap mínimo (bytes) | | ☐ > 100K ☐ < 100K |
| Anomalias detectadas | | ☐ 0 (esperado) |
| Resets/crashes | | ☐ 0 (esperado) ☐ > 0 |
| Linhas corrompidas | | ☐ Não ☐ Sim |
| **Resultado** | | ☐ **PASS** ☐ **FAIL** |

**Observações GOLDEN:**

---

## 5. Execução EXTENDED

| Métrica | Valor | Status |
|---------|-------|--------|
| Logs salvos em | `logs/v8b2_esp32_extended_log.txt` | ☐ Sim ☐ Não |
| Total de records | | |
| Parse errors | | ☐ 0 ☐ > 0 |
| Status OK rate | | ☐ 1.0 ☐ < 1.0 |
| Latência média (ms) | | |
| Latência p95 (ms) | | |
| Latência p99 (ms) | | |
| Latência máxima (ms) | | |
| Heap mínimo (bytes) | | ☐ > 100K ☐ < 100K |
| Variação heap | | (heap_max - heap_min) |
| Anomalias detectadas | | ☐ 0 (esperado) |
| Resets/crashes | | ☐ 0 (esperado) ☐ > 0 |
| Linhas corrompidas | | ☐ Não ☐ Sim |
| **Resultado** | | ☐ **PASS** ☐ **FAIL** |

**Observações EXTENDED:**

---

## 6. Execução ANOMALY

| Métrica | Valor | Status |
|---------|-------|--------|
| Logs salvos em | `logs/v8b2_esp32_anomaly_log.txt` | ☐ Sim ☐ Não |
| Total de records | | |
| Parse errors | | ☐ 0 ☐ > 0 |
| Status OK rate | | ☐ 1.0 ☐ < 1.0 |
| Latência média (ms) | | |
| Latência p95 (ms) | | |
| Latência p99 (ms) | | |
| Latência máxima (ms) | | |
| Heap mínimo (bytes) | | ☐ > 100K ☐ < 100K |
| **Anomalias esperadas** | 10/10 | ☐ Detectadas ☐ Não |
| **Anomalias não detectadas** | | (listar IDs) |
| **Falsos positivos observados** | | (descrever) |
| Resets/crashes | | ☐ 0 (esperado) ☐ > 0 |
| Linhas corrompidas | | ☐ Não ☐ Sim |
| **Resultado** | | ☐ **PASS** ☐ **FAIL** |

**Observações ANOMALY:**

---

## 7. Estabilidade Serial e Sistema

- **Houve reset durante as execuções?** ☐ Não (esperado) ☐ Sim
  - Se sim, quando:
- **Houve travamento (hang)?** ☐ Não ☐ Sim
  - Se sim, em qual modo:
- **Houve perda de conexão serial?** ☐ Não ☐ Sim
  - Se sim, quantas vezes:
- **Houve linhas corrompidas / garbled?** ☐ Não ☐ Sim
  - Se sim, aproximadamente quantas:
- **Houve variação significativa de heap?** ☐ Não ☐ Sim
  - Se sim, qual a variação máxima:
- **Houve lentidão ou timeout?** ☐ Não ☐ Sim
  - Se sim, em qual etapa:

---

## 8. Arquivos de Retorno

Confirme que a pasta `retorno_v8b2_esp32/` contém:

- [ ] `ambiente_esp32.md` — Preenchido com dados de hardware
- [ ] `resultados_execucao.md` — Este documento, preenchido
- [ ] `observacoes_operador.md` — Observações adicionais
- [ ] `v8b2_benchmark_summary.json` — Saída do script validate_returned_logs.py (se gerado)
- [ ] `v8b2_benchmark_metrics.csv` — Saída do script (se gerado)
- [ ] `logs/v8b2_esp32_golden_log.txt` — Log bruto GOLDEN
- [ ] `logs/v8b2_esp32_extended_log.txt` — Log bruto EXTENDED
- [ ] `logs/v8b2_esp32_anomaly_log.txt` — Log bruto ANOMALY

---

## 9. Validação Local (Scripts)

- **Script `validate_returned_logs.py` executado?** ☐ Sim ☐ Não
- **Resultado da validação:** ☐ PASS ☐ FAIL ☐ Não executado
- **Avisos ou erros retornados?** ☐ Nenhum ☐ Descreva:

**Comando utilizado:**
```
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt \
    --json v8b2_benchmark_summary.json \
    --csv v8b2_benchmark_metrics.csv
```

---

## 10. Resumo e Recomendações

### Status Final

- **GOLDEN:** ☐ PASS ☐ FAIL
- **EXTENDED:** ☐ PASS ☐ FAIL
- **ANOMALY:** ☐ PASS ☐ FAIL
- **VALIDAÇÃO LOCAL:** ☐ PASS ☐ FAIL
- **GERAL:** ☐ **TUDO OK** ☐ **REVISAR** ☐ **PROBLEMA**

### Problemas Encontrados

Se houver desvios dos valores esperados, descreva:

1. **Problema:** 
   - **Severidade:** ☐ Crítico ☐ Alto ☐ Médio ☐ Baixo
   - **Ação recomendada:** 

2. **Problema:** 
   - **Severidade:** ☐ Crítico ☐ Alto ☐ Médio ☐ Baixo
   - **Ação recomendada:** 

### Comentários Finais

Qualquer observação relevante sobre o comportamento, estabilidade, performance ou ambiente:

---

## 11. Entrega

- **Data de preenchimento:** 
- **Pasta compactada em ZIP:** `retorno_v8b2_esp32_YYYYMMDD.zip`
- **SHA256 do ZIP (se gerado):** 
- **Pronto para envio:** ☐ Sim ☐ Não

---

**Template versão:** V8B2 · 2026-05-19
