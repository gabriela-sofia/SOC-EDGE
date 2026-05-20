# Quantização

Esta pasta reserva a camada pública para experimentos e handoffs de quantização
do SOC V8B2. Ela ainda não contém firmware INT8 validado.

O baseline público continua sendo a MLP `float32` do pacote V8B2, validada por
replay embarcado na ESP32. A quantização nesta fase é apenas preparação:
footprint, estimativa teórica de redução de memória e simulação de erro de
pesos por dequantização.

Relatórios calculados localmente devem ser gravados em `local_runs/`, que é
ignorado pelo Git. Não versionar modelos binários, logs novos ou saídas
massivas nesta pasta.

Arquivos públicos nesta pasta:

- `canonical_model_weights_v8b2_int8_candidate.h`: header C candidato,
  experimental, derivado do header `float32` canônico;
- `V8B2_INT8_CANDIDATE_MANIFEST.json`: manifesto do candidato, com escopo e
  limites de claim.

Para regenerar o candidato:

```powershell
python scripts/compare_v8b2_quantization_schemes.py
python scripts/export_v8b2_quantized_header.py
```

O header `float32` canônico permanece em
`embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h`. O header INT8
candidate não substitui esse arquivo e ainda não representa firmware INT8
validado.
