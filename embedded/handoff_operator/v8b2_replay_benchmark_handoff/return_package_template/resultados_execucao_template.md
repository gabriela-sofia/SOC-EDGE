# Resultados de Execução — V8B2

**Instruções:** Preencha este documento com resultados dos seus testes. Salve em: `retorno_v8b2_esp32/resultados_execucao.md`

---

## Resumo Executivo

- **Status Final:** ☐ PASS ☐ FAIL ☐ PARCIAL
- **Data de Execução:** 
- **Total de Amostras Processadas:** 
- **Erros de Parse:** 

---

## GOLDEN (Validação Curta)

| Métrica | Valor | Esperado | OK? |
|---------|-------|----------|-----|
| Total Records | | ~20 | ☐ |
| Parse Errors | | 0 | ☐ |
| Status OK Rate | | 1.0 | ☐ |
| Latência Mean (ms) | | 0.16 ±0.05 | ☐ |
| Latência P95 (ms) | | 0.17 ±0.10 | ☐ |
| Latência Max (ms) | | <1.0 | ☐ |
| Heap Min (bytes) | | >100000 | ☐ |
| Anomalias (esperado 0) | | 0 | ☐ |
| Resets/Crashes | | 0 | ☐ |
| **Resultado** | | | ☐ PASS ☐ FAIL |

**Observações GOLDEN:**

---

## EXTENDED (Validação Média)

| Métrica | Valor | Esperado | OK? |
|---------|-------|----------|-----|
| Total Records | | ~120 | ☐ |
| Parse Errors | | 0 | ☐ |
| Status OK Rate | | 1.0 | ☐ |
| Latência Mean (ms) | | 0.13 ±0.05 | ☐ |
| Latência P95 (ms) | | 0.13 ±0.10 | ☐ |
| Latência Max (ms) | | <1.5 | ☐ |
| Heap Min (bytes) | | >100000 | ☐ |
| Heap Variação (max-min) | | <10000 | ☐ |
| Anomalias (esperado 0) | | 0 | ☐ |
| Resets/Crashes | | 0 | ☐ |
| **Resultado** | | | ☐ PASS ☐ FAIL |

**Observações EXTENDED:**

---

## ANOMALY (Cenários Controlados)

| Métrica | Valor | Esperado | OK? |
|---------|-------|----------|-----|
| Total Records | | ~10 | ☐ |
| Parse Errors | | 0 | ☐ |
| Status OK Rate | | 1.0 | ☐ |
| Latência Mean (ms) | | 0.21 ±0.10 | ☐ |
| Latência P95 (ms) | | 0.50 ±0.20 | ☐ |
| Latência Max (ms) | | <2.0 | ☐ |
| Heap Min (bytes) | | >100000 | ☐ |
| **Anomalias Esperadas** | | 10/10 | ☐ |
| Anomalias Detectadas | | | |
| Falsos Positivos | | 0 | ☐ |
| Anomalias Não Detectadas | | | (listar IDs) |
| Resets/Crashes | | 0 | ☐ |
| **Resultado** | | | ☐ PASS ☐ FAIL |

**Observações ANOMALY:**

---

## Estabilidade Geral

- **Houve Reset?** ☐ Não ☐ Sim (descreva quando:)
- **Houve Travamento?** ☐ Não ☐ Sim (descreva:)
- **Perda de Conexão Serial?** ☐ Não ☐ Sim (quantas vezes:)
- **Linhas Corrompidas?** ☐ Não ☐ Sim (aproximadamente:)
- **Variação de Heap Significativa?** ☐ Não ☐ Sim (máxima variação:)
- **Lentidão ou Timeout?** ☐ Não ☐ Sim (descreva:)

---

## Validação Local (Script)

- **Script Executado?** ☐ Sim ☐ Não
- **Resultado:** ☐ PASS ☐ FAIL ☐ Não executado
- **Mensagens de Erro (se houver):**

**Comando Utilizado:**
```
python scripts/validate_returned_logs.py --golden ... --extended ... --anomaly ...
```

---

## Resumo Consolidado

| Aspecto | Status |
|---------|--------|
| GOLDEN | ☐ PASS ☐ FAIL |
| EXTENDED | ☐ PASS ☐ FAIL |
| ANOMALY | ☐ PASS ☐ FAIL |
| Estabilidade | ☐ OK ☐ COM PROBLEMAS |
| **GERAL** | **☐ TUDO OK ☐ REVISAR** |

---

## Problemas Encontrados (se houver)

### Problema 1
- **Descrição:** 
- **Modo Afetado:** GOLDEN / EXTENDED / ANOMALY
- **Severidade:** ☐ Crítico ☐ Alto ☐ Médio ☐ Baixo
- **Ação Recomendada:** 

### Problema 2
- **Descrição:** 
- **Modo Afetado:** GOLDEN / EXTENDED / ANOMALY
- **Severidade:** ☐ Crítico ☐ Alto ☐ Médio ☐ Baixo
- **Ação Recomendada:** 

---

## Dados Brutos Fornecidos

- ☐ `v8b2_esp32_golden_log.txt` (bruto)
- ☐ `v8b2_esp32_extended_log.txt` (bruto)
- ☐ `v8b2_esp32_anomaly_log.txt` (bruto)
- ☐ `v8b2_benchmark_summary.json` (gerado)
- ☐ `v8b2_benchmark_metrics.csv` (gerado)

---

**Preenchido em:** 2026-__-__  
**Operador:** __________________
