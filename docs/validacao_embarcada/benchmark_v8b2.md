# Benchmark embarcado V8B2

Este documento define a camada de benchmark do pacote SOC V8B2. O objetivo é
medir características operacionais do replay embarcado já validado na ESP32,
sem ampliar o claim científico do projeto.

## Escopo

O benchmark analisa logs seriais do replay V8B2 e extrai métricas de runtime,
latência, heap, parsing, modos executados e status por amostra. Ele não mede
aquisição de sensor físico real, validação em campo, produção ou operação
contínua 24/7.

O próximo estágio experimental continua sendo o V8C, com validação de bancada
por aquisição real ou semi-real.

## Logs canônicos analisáveis

Os logs V8B2 versionados nesta base são:

| Modo | Log |
| --- | --- |
| GOLDEN | `embedded/handoff_v8b2/v8b2_esp32_golden_log.txt` |
| EXTENDED | `embedded/handoff_v8b2/v8b2_esp32_extended_log.txt` |
| ANOMALY | `embedded/handoff_v8b2/v8b2_esp32_anomaly_log.txt` |

## Parser

O parser público é:

```powershell
python scripts/parse_v8b2_benchmark.py embedded/handoff_v8b2/v8b2_esp32_golden_log.txt
```

Para analisar os três logs:

```powershell
python scripts/parse_v8b2_benchmark.py embedded/handoff_v8b2/v8b2_esp32_golden_log.txt embedded/handoff_v8b2/v8b2_esp32_extended_log.txt embedded/handoff_v8b2/v8b2_esp32_anomaly_log.txt
```

Saídas locais opcionais podem ser gravadas fora do Git:

```powershell
python scripts/parse_v8b2_benchmark.py embedded/handoff_v8b2/v8b2_esp32_golden_log.txt embedded/handoff_v8b2/v8b2_esp32_extended_log.txt embedded/handoff_v8b2/v8b2_esp32_anomaly_log.txt --json local_runs/v8b2_benchmark_summary.json --csv local_runs/v8b2_benchmark_metrics.csv
```

## Métricas extraídas

Por modo, o parser calcula:

- número de registros válidos;
- erros de parsing;
- status OK e status de falha;
- contagem e taxa de `anomaly_flag`;
- média, mediana, p95, p99 e máximo de latência;
- mínimo e média de heap livre;
- mínimo de `min_free_heap` e `max_alloc_heap`;
- faixa de `sample_id`, contagem única e duplicidade.

Globalmente, o parser calcula total de registros, erros de parsing, modos
observados, média e p95 de latência, heap livre mínimo e taxa geral de status OK.

## Resultado consolidado dos logs versionados

Execução local do parser sobre os três logs versionados:

| Modo | Registros | Latência média (ms) | Latência p95 (ms) | Heap livre mínimo (bytes) | Status OK | Falhas | Taxa de anomalia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GOLDEN | 20 | 0.164050 | 0.165850 | 351068 | 20 | 0 | 0.000000 |
| EXTENDED | 120 | 0.134533 | 0.130000 | 351068 | 120 | 0 | 0.000000 |
| ANOMALY | 10 | 0.206900 | 0.501500 | 351092 | 10 | 0 | 1.000000 |

Métricas globais:

- registros válidos: 150;
- erros de parsing: 0;
- modos observados: ANOMALY, EXTENDED e GOLDEN;
- latência média geral: 0.143293 ms;
- p95 geral de latência: 0.141550 ms;
- heap livre mínimo geral: 351068 bytes;
- taxa geral de status OK: 1.000000.

## Interpretação conservadora

Os resultados sustentam apenas que os logs de replay embarcado V8B2 mantêm
latência baixa, heap estável e parsing íntegro nos artefatos versionados. Isso é
compatível com o claim já consolidado de replay embarcado validado na ESP32.

Claims ainda proibidos:

- validação em campo;
- pronto para produção;
- sensor físico real validado no V8B2;
- operação 24/7 validada;
- validação industrial;
- diagnóstico operacional de degradação ou predição de vida útil.
