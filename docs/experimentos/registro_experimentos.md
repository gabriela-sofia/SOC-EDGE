# Registro de Experimentos

| Fase | Objetivo | Saída esperada |
|---|---|---|
| Normalização | Padronizar unidades, ciclos e features | Dataset preparado e schema |
| Method B | Derivar alvo SOC físico-estimado | `soc_method_b` |
| Cross-domain | Testar transferência entre domínios | Relatórios de desempenho |
| MLP leve | Selecionar modelo embarcável | Pesos, scaler e feature order |
| Export/parity | Garantir equivalência Python/firmware | Relatório de paridade |
| Replay ESP32 | Executar vetores canônicos no hardware | Logs e PASS/FAIL |
| Anomalias | Testar fault injection controlado | Flags esperadas e resultado |

Experimentos antigos devem permanecer documentados quando explicam decisões metodológicas, mas não devem competir com o estado consolidado V8B2.
