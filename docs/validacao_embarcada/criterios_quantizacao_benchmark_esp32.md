# Criterios V8C: quantizacao e benchmark ESP32

## Regra geral

A candidata quantizada ou compactada so pode receber PASS experimental se preservar a paridade relevante contra a MLP float V8B2 e se nao quebrar o contrato canonico de entrada, scaler e clipping. A ausencia de dados deve resultar em status explicito, nunca em aprovacao implicita.

## Criterios PASS/FAIL

| Criterio | PASS | FAIL |
|---|---|---|
| Compilacao do firmware | Firmware compila para ESP32 sem mudanca de target ou troca de placa | Falha de compilacao, troca de ESP32 ou mudanca de alvo |
| Replay GOLDEN | Todos os vetores GOLDEN sao executados e comparados | Vetores faltantes, schema invalido ou regressao numerica critica |
| Replay EXTENDED | Todos os vetores EXTENDED sao executados e comparados | Amostras ausentes, ordem de features alterada ou erro acima do limite |
| Anomalias | Cenarias ANOMALY nao apresentam regressao critica contra V8B2 | Falha de schema, NaN/inf, ou perda relevante de comportamento esperado |
| Paridade Python vs ESP32 | Diferenca entre referencia Python e log ESP32 dentro do limite definido | Divergencia nao explicada ou logs insuficientes |
| Latencia media | Media registrada e comparavel entre float e candidata | Campo ausente ou medicao nao reprodutivel |
| Latencia p95 | p95 registrada quando houver amostras suficientes | p95 omitida quando houver dados suficientes |
| RAM/heap | `free_heap` e, se disponivel, `min_free_heap` registrados | Sem metrica de memoria ou queda critica sem justificativa |
| Flash/binario | Tamanho aproximado registrado quando disponivel | Tamanho omitido quando a ferramenta de build fornece o valor |
| MAE/RMSE contra baseline Python | MAE e RMSE calculados contra baseline float Python | Metricas ausentes ou calculadas contra referencia errada |
| Diferenca maxima float vs candidata | `max_abs_diff` dentro do limite experimental configurado | Diferenca maxima acima do limite ou sem auditoria |
| NaN/inf | Nenhum SOC, erro ou metrica numerica contem NaN/inf | Qualquer NaN/inf em saida ou metrica essencial |
| Clipping final | SOC final sempre clipado para `[0, 1]` | Feature escalada clipada ou SOC final fora de `[0, 1]` |

## Limites iniciais

Enquanto nao houver logs reais da candidata, os limites devem ser tratados como criterios de triagem:

- `max_abs_diff` float versus candidata: ate `0.01` SOC para aceitacao experimental inicial.
- MAE contra baseline Python: ate `0.005` SOC.
- RMSE contra baseline Python: ate `0.01` SOC.
- Nenhum NaN/inf e tolerado.
- O candidato nao substitui o baseline V8B2 sem revisao explicita.

