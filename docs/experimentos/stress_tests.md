# Plano de Stress Tests

Os stress tests avaliam robustez operacional do pipeline embarcado além do replay curto. Eles são planejamento experimental e não constituem validação executada até que logs e relatórios sejam adicionados.

## Dimensões

| Dimensão | Objetivo | Métrica |
|---|---|---|
| Long-run | Verificar estabilidade por execução prolongada | duração, resets, perda de serial |
| Memória | Detectar queda de heap ou fragmentação | `free_heap`, `min_free_heap`, tendência temporal |
| Inferência contínua | Avaliar latência sob carga repetida | média, p95, máximo |
| Watchdog | Confirmar recuperação de travamentos | eventos de watchdog e reinício |
| Serial | Avaliar perda e recuperação de comunicação | linhas perdidas, reconexões |
| Overflow temporal | Testar comportamento de contadores e timestamps | monotonicidade e wrap controlado |

## Critérios Conservadores

- PASS exige log auditável e ausência de falhas bloqueantes.
- WARN exige falha recuperável e explicada.
- FAIL ocorre quando a falha impede auditoria, corrompe dados ou causa reset não esperado.

## Saídas

- log bruto;
- resumo de métricas;
- decisão PASS/WARN/FAIL;
- descrição do setup;
- limitações observadas.
