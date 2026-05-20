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
