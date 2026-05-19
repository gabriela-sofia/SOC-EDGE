# Benchmarks embarcados

Esta pasta registra a camada pública de benchmark do pacote SOC V8B2. Neste
repositório, benchmark significa análise de logs de replay embarcado na ESP32:
tempo de inferência, heap livre, integridade de parsing, modos executados e
estabilidade observável no arquivo serial.

O benchmark não representa validação em campo, produção, sensor físico real no
V8B2 ou operação contínua 24/7. O escopo permanece restrito ao replay embarcado
do pacote V8B2 e a logs com o schema público:

```text
sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status
```

As métricas extraídas incluem contagem de registros, erros de parsing, status,
taxa de anomalia, média, mediana, p95, p99 e máximo de latência, mínimos de heap
e duplicidade de `sample_id`. Saídas locais de benchmark devem ser gravadas em
`local_runs/`, que não faz parte do Git.
