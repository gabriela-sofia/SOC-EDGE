# Candidata quantizada V8C

## Origem

Este header foi gerado a partir do header float canonico `embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h`. A MLP V7C/V8B2 float continua sendo o baseline canonico.

## Tipo de compactacao

A candidata usa quantizacao deterministica simetrica INT8 por array para pesos e bias (`W0`, `B0`, `W1`, `B1`, `W2`, `B2`). Cada array possui escala propria. O scaler de entrada permanece em float e segue a politica conceitual do `sklearn.MinMaxScaler`.

## Contrato preservado

- Mesma ordem de features: `voltage_v`, `temperature_c`, `current_ma`, `delta_voltage`, `delta_temperature`, `delta_current`.
- `current_ma` e `delta_current` em mA.
- Mesma sequencia de camadas da MLP baseline.
- Sem clipping das features escaladas.
- Clipping apenas do SOC final para `[0, 1]`.
- ESP32 permanece inference-only.

## Como comparar

Executar `scripts/v8c_python_float_vs_candidate_benchmark.py` para comparar a inferencia float Python contra a candidata dequantizada simulada. Para ESP32, compilar uma variante experimental que inclua `candidate_quantized_model.h` e devolver os logs no template V8C.

## Limitacoes

Esta candidata e experimental. Na comparacao offline inicial com 140 amostras GOLDEN + EXTENDED, o `max_abs_diff` contra o baseline float ficou em aproximadamente `0.038904`, acima do limite conservador inicial de `0.01`. Portanto, ela esta implementada para benchmark e handoff experimental, mas ainda nao deve ser tratada como candidata aprovada.

Ela nao substitui o baseline V8B2, nao cria claim de campo, nao cria claim de producao, nao cria claim de sensor fisico real, nao cria claim de operacao 24/7, nao cria claim de SOH operacional e nao cria claim de diagnostico real de degradacao.
