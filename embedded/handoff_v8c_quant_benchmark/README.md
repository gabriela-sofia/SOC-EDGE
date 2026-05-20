# Handoff V8C: quantizacao e benchmark ESP32

## Finalidade e objetivo

Este handoff prepara uma comparacao experimental entre a MLP float V8B2 e uma candidata quantizada ou compactada. Ele nao apaga nem substitui `embedded/handoff_v8b2/`; o V8B2 continua sendo o baseline canonico.

## Relacao com V8B2

A pessoa da ESP32 deve usar os mesmos vetores de replay e anomalia do V8B2 como referencia de entrada. A candidata so e avaliada de forma justa se preservar:

- target Method B / `soc_q_cycle`;
- ordem canonica das features;
- `current_ma` em mA;
- scaler equivalente ao `sklearn.MinMaxScaler`;
- ausencia de clipping nas features escaladas;
- clipping apenas do SOC final para `[0, 1]`.

## Arquivos a usar

- Firmware baseline: `embedded/handoff_v8b2/firmware/firmware_soc_v8b2_canonical.ino`.
- Pesos/scaler baseline: `embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h`.
- Header do primeiro candidato experimental: `embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model.h`.
- Header do candidato otimizado experimental, quando presente: `embedded/handoff_v8c_quant_benchmark/include/candidate_quantized_model_optimized.h`.
- Documentacao da candidata: `embedded/handoff_v8c_quant_benchmark/include/README_candidate_quantized.md`.
- Vetores C baseline: `embedded/handoff_v8b2/include/replay_vectors_v8b2.h`.
- Replays: `embedded/handoff_v8b2/replay/`.
- Anomalias: `embedded/handoff_v8b2/anomaly/`.
- Manifestos V8C: `embedded/handoff_v8c_quant_benchmark/manifests/`.
- Templates de retorno: `embedded/handoff_v8c_quant_benchmark/reports/`.

## Logs que precisam voltar

Para cada firmware testado, devolver logs GOLDEN, EXTENDED e ANOMALY. Usar `model_variant=baseline_float` para o baseline, `model_variant=v8c_int8_per_array_candidate` para o primeiro candidato e `model_variant=v8c_optimized_candidate` para a variante otimizada, quando compilada.

Cada log deve conter:

- `sample_id`;
- `mode`;
- `model_variant`;
- `soc_final`;
- `inference_time_ms`;
- `heap_free`;
- `heap_min_free`, se disponivel;
- `max_alloc_heap`, se disponivel;
- `flash_bytes` ou tamanho aproximado do binario, se disponivel;
- `anomaly_flag`;
- `status`.

## Metricas obrigatorias

- MAE, RMSE e `max_abs_diff` contra baseline Python float.
- Diferenca float versus candidata.
- Latencia media.
- Latencia p95 quando houver amostras suficientes.
- Heap livre e heap minimo quando disponivel.
- Tamanho aproximado de flash/binario quando disponivel.
- Confirmacao de ausencia de NaN/inf.
- Confirmacao de SOC final sempre em `[0, 1]`.

## Aceite

O primeiro candidato V8C usa INT8 simetrico por array e fica preservado para rastreabilidade. O candidato otimizado, quando usado, e uma alternativa experimental de benchmark e nao substitui automaticamente o baseline nem o primeiro candidato.

A candidata quantizada ou compactada so pode ser aceita como candidata experimental se nao perder paridade de forma relevante e se os logs reais da ESP32 confirmarem a execucao. A aprovacao experimental nao cria claim de campo, nao cria claim de producao, nao cria claim de sensor fisico real, nao cria claim de operacao 24/7, nao cria claim de SOH operacional e nao cria claim de diagnostico real de degradacao.
