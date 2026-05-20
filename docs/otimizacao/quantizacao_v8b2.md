# Quantização V8B2: prontidão e footprint

## Objetivo da Fase 3A

Esta fase cria uma camada reprodutível para medir o footprint do modelo
canônico V8B2 e simular quantização/dequantização dos pesos em Python. O escopo
é preparatório: não há firmware INT8 validado, não há benchmark embarcado
quantizado e a MLP `float32` do V8B2 continua sendo o baseline canônico.

## Relevância para ESP32

A ESP32 clássica tem restrições de RAM, flash e tempo de inferência. Uma versão
quantizada pode reduzir footprint e abrir espaço para comparações futuras, mas
essa hipótese precisa ser testada em firmware real antes de qualquer claim de
latência, estabilidade ou equivalência embarcada.

## Artefato analisado

O header canônico analisado é:

```text
embedded/handoff_v8b2/include/canonical_model_weights_v8b2.h
```

O header contém uma MLP `float32` com entrada de 6 features, camadas densas
64 e 32, saída linear, scaler MinMax e regra de clip final para SOC em `[0, 1]`.

## Como rodar

Análise de footprint:

```powershell
python scripts/analyze_v8b2_model_footprint.py
```

Simulação de quantização/dequantização de pesos:

```powershell
python scripts/simulate_v8b2_weight_quantization.py
```

O segundo comando grava um JSON pequeno em `local_runs/quantization_v8b2/`, que
é uma área local ignorada pelo Git.

## O que foi medido

O script de footprint parseia `#define` e arrays `static const float` do header,
conta parâmetros por array e estima bytes em `float32` e `int8`.

O script de quantização aplica quantização simétrica int8 por tensor:

```text
scale = max_abs / 127
q = round(x / scale), limitado a [-127, 127]
x_dequant = q * scale
```

Para cada array, o relatório calcula mínimo, máximo, média, `max_abs`, escala,
erro absoluto máximo, erro absoluto médio e RMSE.

## Resultado do header versionado

Execução sobre `canonical_model_weights_v8b2.h`:

| Métrica | Valor |
| --- | ---: |
| Arrays `float` parseados | 8 |
| Valores `float` totais no header | 2573 |
| Parâmetros do modelo (`W*` e `B*`) | 2561 |
| Footprint total estimado em `float32` | 10292 bytes |
| Footprint total estimado em `int8` | 2573 bytes |
| Footprint do modelo em `float32` | 10244 bytes |
| Footprint do modelo em `int8` | 2561 bytes |
| Compressão teórica | 4.0x |

Na simulação de quantização/dequantização dos parâmetros do modelo:

| Métrica | Valor |
| --- | ---: |
| `max_abs` dos parâmetros do modelo | 1.55858812 |
| Escala global informativa dos parâmetros | 0.0122723474 |
| Erro absoluto máximo | 0.0061357552 |
| Erro absoluto médio | 0.0020997971 |
| RMSE | 0.0029317634 |

O script também calcula métricas por array. Os arrays do scaler são parseados e
registrados, mas não são tratados como parâmetros da MLP no resumo global de
quantização de pesos.

## Interpretação conservadora

Esta fase permite estimar redução teórica de memória e erro numérico de pesos
após dequantização. Ela não mede saída SOC, latência em ESP32, uso real de heap
em firmware quantizado nem paridade embarcada.

Claims proibidos nesta fase:

- INT8 embarcado validado;
- melhoria de latência;
- equivalência Python vs ESP32 para firmware quantizado;
- validação em campo;
- pronto para produção;
- sensor físico real validado no V8B2;
- operação 24/7 validada.

## Próximos passos

- Fase 3B: implementar inferência quantizada, fixed-point ou TFLite Micro INT8
  de forma comparável ao baseline `float32`.
- Fase 3C: medir ESP32 `float32` vs quantizado com os mesmos vetores, critérios
  de paridade, latência, heap e estabilidade.

## Fase 3B: comparação de inferência float vs pesos dequantizados

Esta etapa reconstrói a MLP `float32` a partir do header V8B2 e compara sua
saída com uma segunda MLP em Python usando pesos e biases quantizados e
dequantizados por tensor. O scaler é aplicado como no firmware:

```text
x_scaled[i] = (x[i] - SCALER_MIN[i]) * SCALER_SCALE[i]
```

As features escaladas não são clipadas. O clip é aplicado apenas ao SOC final
em `[0, 1]`.

Comando:

```powershell
python scripts/compare_v8b2_float_vs_dequantized.py
```

O script usa automaticamente, quando presentes:

- `embedded/handoff_v8b2/replay/canonical_golden_vectors_v8b2.csv`;
- `embedded/handoff_v8b2/replay/canonical_extended_replay_v8b2.csv`.

As saídas calculadas são locais e ficam em `local_runs/quantization_v8b2/`:

- `v8b2_float_vs_dequantized_predictions.csv`;
- `v8b2_float_vs_dequantized_summary.json`.

Métricas calculadas sobre os replays versionados:

| Métrica | Valor |
| --- | ---: |
| Amostras | 140 |
| Diferença absoluta máxima | 0.0389042245 |
| Diferença absoluta média | 0.0100143235 |
| RMSE da diferença | 0.0133678754 |
| p95 da diferença absoluta | 0.0276084677 |
| Diferença assinada máxima | 0.0389042245 |
| Diferença assinada média | 0.0090401339 |

Como os CSVs usados contêm `soc_clipped_reference`, a comparação também registra
erro contra a referência canônica. A interpretação primária desta fase, porém,
é a diferença entre a MLP `float32` reconstruída e a MLP com pesos
dequantizados.

Limites:

- não é firmware INT8 embarcado;
- não mede latência;
- não substitui replay ESP32;
- não altera o baseline canônico V8B2 `float32`;
- não autoriza claim de campo, produção, sensor físico real ou operação 24/7.

Próximo passo: Fase 3C, com implementação de caminho quantizado/fixed-point ou
preparação de export TFLite Micro INT8, seguida de comparação na ESP32 contra o
baseline `float32`.

## Fase 3C: comparação de esquemas e header quantizado candidato

Esta fase compara estratégias offline de quantização de pesos e exporta um
header C candidato para experimentos futuros. O objetivo é escolher um ponto de
partida auditável para firmware quantizado, sem afirmar que o caminho INT8 já
foi validado na ESP32.

Comandos:

```powershell
python scripts/compare_v8b2_quantization_schemes.py
python scripts/export_v8b2_quantized_header.py
```

Esquemas comparados:

- `global_symmetric_int8`: uma escala única para todos os pesos e biases;
- `per_array_symmetric_int8`: uma escala por array (`W0`, `B0`, `W1`, `B1`,
  `W2`, `B2`);
- `per_layer_group_symmetric_int8`: uma escala por grupo de camada
  (`W0+B0`, `W1+B1`, `W2+B2`).

Ranking observado por RMSE entre MLP `float32` e pesos dequantizados:

| Posição | Esquema |
| ---: | --- |
| 1 | `per_array_symmetric_int8` |
| 2 | `per_layer_group_symmetric_int8` |
| 3 | `global_symmetric_int8` |

Métricas do melhor esquema:

| Métrica | Valor |
| --- | ---: |
| Amostras | 140 |
| Diferença absoluta média | 0.0100143235 |
| RMSE da diferença | 0.0133678754 |
| p95 da diferença absoluta | 0.0276084677 |
| Diferença absoluta máxima | 0.0389042245 |
| Compressão teórica | 4.0x |
| Número de escalas | 6 |

Arquivos candidatos versionados:

- `embedded/quantization/canonical_model_weights_v8b2_int8_candidate.h`;
- `embedded/quantization/V8B2_INT8_CANDIDATE_MANIFEST.json`.

Diferenças de escopo:

- `float32` canônico: referência pública validada por replay embarcado V8B2;
- pesos dequantizados offline: simulação Python para estimar impacto numérico;
- header INT8 candidato: artefato textual para experimentos futuros;
- firmware INT8 validado: ainda não existe neste estágio.

Limites:

- não há claim de firmware INT8 embarcado;
- não há claim de melhoria de latência;
- não substitui replay ESP32;
- não altera o baseline `float32`;
- não autoriza campo, produção, sensor físico real ou operação 24/7.

Próximos passos:

- Fase 3D: implementar caminho experimental no firmware ou uma referência
  fixed-point auditável;
- Fase 3E: comparar ESP32 `float32` vs candidato quantizado com os mesmos
  critérios de paridade, latência, heap e estabilidade.
