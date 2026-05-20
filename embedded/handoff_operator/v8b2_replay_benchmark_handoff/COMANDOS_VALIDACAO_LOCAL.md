# Comandos de Validação Local — V8B2

Após coletar seus logs da ESP32, use estes comandos para validar localmente.

---

## Setup Inicial

### 1. Abra terminal na raiz do ZIP

Navegar para pasta principal:
```bash
cd C:\...\SOC_EDGE_V8B2_ESP32_HANDOFF
```

Ou (macOS/Linux):
```bash
cd ~/Downloads/SOC_EDGE_V8B2_ESP32_HANDOFF
```

### 2. Confirme que Python está disponível

```bash
python --version
```

Esperado: Python 3.10 ou superior.

### 3. Confirme que logs foram salvos

```bash
ls logs/
```

Esperado:
```
v8b2_esp32_golden_log.txt
v8b2_esp32_extended_log.txt
v8b2_esp32_anomaly_log.txt
```

---

## Comandos de Validação

### Validação Completa (3 Logs)

Comando mais comum; valida todos os 3 replays e gera summary JSON + CSV:

```bash
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt \
    --json v8b2_benchmark_summary.json \
    --csv v8b2_benchmark_metrics.csv
```

**Esperado:**
```
V8B2 validation
Total records: 150
Parse errors: 0
Status: PASS
```

**Saída:**
- `v8b2_benchmark_summary.json` — Resumo em JSON
- `v8b2_benchmark_metrics.csv` — Métricas em CSV

---

### Validação Apenas GOLDEN

Se só tem GOLDEN pronto:

```bash
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt
```

---

### Validação Apenas EXTENDED

```bash
python scripts/validate_returned_logs.py \
    --extended logs/v8b2_esp32_extended_log.txt
```

---

### Validação Apenas ANOMALY

```bash
python scripts/validate_returned_logs.py \
    --anomaly logs/v8b2_esp32_anomaly_log.txt
```

---

### Validação com Output Customizado

Salvar resultados em diretório específico:

```bash
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt \
    --json retorno_v8b2_esp32/v8b2_benchmark_summary.json \
    --csv retorno_v8b2_esp32/v8b2_benchmark_metrics.csv
```

---

## Interpretação de Saída

Exemplo de saída bem-sucedida:

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
  "anomaly_rate": 0.067,
  "duplicate_sample_id_count": 0,
  "resets_observados": 0,
  "modo_breakdown": {
    "GOLDEN": {
      "n": 20,
      "lat_mean_ms": 0.164050,
      "lat_p95_ms": 0.165850,
      "heap_min": 351068,
      "status_ok": 20,
      "anomaly_rate": 0.0
    },
    "EXTENDED": {
      "n": 120,
      "lat_mean_ms": 0.134533,
      "lat_p95_ms": 0.130000,
      "heap_min": 351068,
      "status_ok": 120,
      "anomaly_rate": 0.0
    },
    "ANOMALY": {
      "n": 10,
      "lat_mean_ms": 0.206900,
      "lat_p95_ms": 0.501500,
      "heap_min": 351092,
      "status_ok": 10,
      "anomaly_rate": 1.0
    }
  }
}
```

### Chaves Importantes

| Chave | Esperado | Crítico |
|-------|----------|---------|
| `total_records` | 150 (20+120+10) | Deve ter > 0 |
| `parse_errors` | 0 | **Crítico:** deve ser 0 |
| `status_ok_rate` | 1.0 | **Crítico:** deve ser 1.0 |
| `latency_mean_ms` | ~0.14 | Informativo; < 1.0 é OK |
| `latency_p95_ms` | ~0.15 | Informativo; < 1.0 é OK |
| `free_heap_min_bytes` | > 100000 | Crítico: < 50000 é perigoso |
| `anomaly_rate` | GOLDEN/EXTENDED: 0.0; ANOMALY: 1.0 | Informativo |
| `resets_observados` | 0 | Crítico: > 0 é problema |

---

## Análise Manual de Logs

Se script retornar erro, diagnosticar manualmente:

### Listar primeiras linhas do log

```bash
head -20 logs/v8b2_esp32_golden_log.txt
```

**Esperado:**
```
sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status
1,GOLDEN,0.855,0.164,351068,351068,12288,0,0,OK
2,GOLDEN,0.856,0.165,351068,351068,12288,0,0,OK
```

### Contar número de linhas

```bash
wc -l logs/v8b2_esp32_golden_log.txt
```

**Esperado:** ~21 linhas (20 registros + header)

### Procurar por erros ou parse failures

```bash
# Procurar por status != OK
grep -v ",OK$" logs/v8b2_esp32_golden_log.txt
```

**Esperado:** Nada (nenhuma linha com status != OK)

### Procurar por linhas corrompidas

```bash
# Procurar por linhas com número de campos incorreto
awk -F',' '{if (NF != 10) print NR": "$0}' logs/v8b2_esp32_golden_log.txt
```

**Esperado:** Nenhuma linha (todas com 10 campos)

---

## Comparação com Referência

Comparar seus resultados com referência laboratório:

### Abrir arquivo de referência

```bash
cat results_golden/v8b2_golden_comparison.csv
```

**Estrutura esperada:**
```
metric,expected,your_value,within_tolerance
latency_mean,0.164,0.165,true
latency_p95,0.166,0.165,true
heap_min,351068,351068,true
status_ok_rate,1.0,1.0,true
```

### Calcular diferença (manualmente)

Se seu `latency_mean` é 0.165 e esperado é 0.164:
- Diferença: 0.001 ms
- Percentual: (0.001 / 0.164) × 100 = 0.6% ✓ (dentro de tolerância)

Se valor desviar muito (> 30% em latência), anote em templates e investigar.

---

## Windows PowerShell

Se preferir interface PowerShell:

```powershell
# Validação completa
python scripts/validate_returned_logs.py `
    --golden logs/v8b2_esp32_golden_log.txt `
    --extended logs/v8b2_esp32_extended_log.txt `
    --anomaly logs/v8b2_esp32_anomaly_log.txt `
    --json v8b2_benchmark_summary.json `
    --csv v8b2_benchmark_metrics.csv
```

Ou usar wrapper PowerShell (se disponível):

```powershell
.\scripts\validate_returned_logs.ps1 `
    -GoldenLog logs/v8b2_esp32_golden_log.txt `
    -ExtendedLog logs/v8b2_esp32_extended_log.txt `
    -AnomalyLog logs/v8b2_esp32_anomaly_log.txt `
    -OutputJson v8b2_benchmark_summary.json `
    -OutputCsv v8b2_benchmark_metrics.csv
```

---

## Resumo Rápido de Check

Após validação, verificar rapidamente:

```bash
# 1. JSON gerado?
ls -lh v8b2_benchmark_summary.json

# 2. Conteúdo está OK?
grep "parse_errors.*0" v8b2_benchmark_summary.json

# 3. Latência dentro do esperado?
grep "latency_mean" v8b2_benchmark_summary.json

# 4. Heap tem espaço suficiente?
grep "free_heap_min" v8b2_benchmark_summary.json
```

---

## Troubleshooting de Comandos

### "python: command not found"

```bash
# Tente
python3 --version

# Se funcionar, use python3 nos comandos acima
python3 scripts/validate_returned_logs.py ...
```

### "FileNotFoundError: logs/v8b2_esp32_golden_log.txt"

```bash
# Confirme que logs existem
ls logs/

# Se não, salve os logs primeiro do Serial Monitor
```

### "ModuleNotFoundError: No module named 'csv'"

Seu Python pode não estar no PATH. Tente:

```bash
# Windows
python -m scripts.validate_returned_logs --golden logs/v8b2_esp32_golden_log.txt

# Ou
pip install --upgrade pip
python scripts/validate_returned_logs.py ...
```

---

## Workflow Completo Exemplo

```bash
# 1. Navegar para pasta
cd SOC_EDGE_V8B2_ESP32_HANDOFF

# 2. Validar
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt \
    --json v8b2_benchmark_summary.json \
    --csv v8b2_benchmark_metrics.csv

# 3. Ver saída
cat v8b2_benchmark_summary.json | grep -E "parse_errors|status_ok_rate|latency_mean"

# 4. Copiar para pasta de retorno
mkdir -p retorno_v8b2_esp32
cp v8b2_benchmark_summary.json retorno_v8b2_esp32/
cp v8b2_benchmark_metrics.csv retorno_v8b2_esp32/
cp logs/v8b2_esp32_*.txt retorno_v8b2_esp32/logs/

# 5. Preencher templates
# (abrir return_package_template/ambiente_esp32_template.md, etc.)
# ... editar ...
cp return_package_template/ambiente_esp32_template.md retorno_v8b2_esp32/ambiente_esp32.md
cp return_package_template/resultados_execucao_template.md retorno_v8b2_esp32/resultados_execucao.md
cp return_package_template/observacoes_operador_template.md retorno_v8b2_esp32/observacoes_operador.md

# 6. Compactar
zip -r retorno_v8b2_esp32.zip retorno_v8b2_esp32/

# 7. Pronto para envio
ls -lh retorno_v8b2_esp32.zip
```

---

## Dica Importante

**Salve sempre seus comandos em um arquivo .txt ou .sh para referência futura.**

Exemplo (`validate_v8b2.sh`):
```bash
#!/bin/bash
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt \
    --json v8b2_benchmark_summary.json \
    --csv v8b2_benchmark_metrics.csv
echo "Validação completa. Ver v8b2_benchmark_summary.json"
```

Execute:
```bash
bash validate_v8b2.sh
```

---

**Versão:** V8B2 · 2026-05-19
