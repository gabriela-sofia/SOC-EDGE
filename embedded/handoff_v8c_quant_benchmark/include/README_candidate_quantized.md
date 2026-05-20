# Candidata quantizada V8C

## Origem

Este header foi gerado a partir do header float canonico `embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h`. A MLP V7C/V8B2 float continua sendo o baseline canonico.

## Tipo de compactacao

A candidata usa quantizacao deterministica simetrica INT8 por array para pesos e bias (`W0`, `B0`, `W1`, `B1`, `W2`, `B2`). Cada array possui escala propria. O scaler de entrada permanece em float e segue a politica conceitual do `sklearn.MinMaxScaler`.

Uma variante otimizada pode existir em `candidate_quantized_model_optimized.h`. Na versao atual, ela preserva a arquitetura e usa pesos INT16 simetricos por neuronio de saida com bias em float. Essa variante foi criada apenas para comparacao experimental porque o primeiro candidato INT8 per-array ficou fora do limite conservador inicial de paridade.

## Contrato preservado

- Mesma ordem de features: `voltage_v`, `temperature_c`, `current_ma`, `delta_voltage`, `delta_temperature`, `delta_current`.
- `current_ma` e `delta_current` em mA.
- Mesma sequencia de camadas da MLP baseline.
- Sem clipping das features escaladas.
- Clipping apenas do SOC final para `[0, 1]`.
- ESP32 permanece inference-only.

## Como comparar

Executar `scripts/v8c_python_float_vs_candidate_benchmark.py` para comparar a inferencia float Python contra as variantes candidatas dequantizadas simuladas. Para ESP32, compilar uma variante experimental que inclua `candidate_quantized_model.h` e, quando aplicavel, outra que inclua `candidate_quantized_model_optimized.h`. Devolver os logs no template V8C preservando `model_variant`.

## Limitacoes

Esta candidata e experimental. Na comparacao offline inicial com 140 amostras GOLDEN + EXTENDED, o primeiro candidato INT8 per-array teve `max_abs_diff` contra o baseline float de aproximadamente `0.038904`, acima do limite conservador inicial de `0.01`.

A variante otimizada INT16 per-output com bias float reduziu o `max_abs_diff` offline para aproximadamente `0.000100`, dentro do limite conservador inicial. Isso e apenas resultado de benchmark offline; a variante ainda depende de execucao real na ESP32 para latencia, heap, tamanho de binario e paridade embarcada.

Nenhuma variante substitui o baseline V8B2, nenhuma cria claim de campo, nenhuma cria claim de producao, nenhuma cria claim de sensor fisico real, nenhuma cria claim de operacao 24/7, nenhuma cria claim de SOH operacional e nenhuma cria claim de diagnostico real de degradacao.
