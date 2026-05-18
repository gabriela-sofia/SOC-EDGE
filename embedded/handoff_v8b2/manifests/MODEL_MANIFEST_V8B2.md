# Manifest do Modelo V8B2

## Identificação

| Campo | Valor |
|---|---|
| Pacote | V8B2 canonical handoff |
| Modelo base | V7C canonical |
| Alvo de treino | `soc_method_b` |
| Arquitetura | `Input(6) -> Dense(64, ReLU) -> Dense(32, ReLU) -> Dense(1, linear)` |
| Parâmetros | 2561 |
| Status V8B2 | Replay embarcado validado na ESP32 |

## Ordem Canônica das Features

| Índice | Nome | Unidade | Observação |
|---|---|---|---|
| 0 | `voltage_v` | V | Tensão terminal da célula |
| 1 | `temperature_c` | C | Temperatura da bateria |
| 2 | `current_ma` | mA | Corrente em miliampere; não usar ampere |
| 3 | `delta_voltage` | V | `voltage_v[t] - voltage_v[t-1]` |
| 4 | `delta_temperature` | C | `temperature_c[t] - temperature_c[t-1]` |
| 5 | `delta_current` | mA | `current_ma[t] - current_ma[t-1]` |

## Scaler MinMax

```text
data_min = [3.87000000, 9.41000000, 50.10000000, -0.06000000, -19.03000000, -226.10000000]
data_max = [4.21000000, 40.19000000, 326.30000000, 0.19000000, 11.32000000, 129.10000000]
scale    = [2.94117647, 0.03248863, 0.00362056, 4.00000000, 0.03294893, 0.00281532]

x_scaled[i] = (x[i] - data_min[i]) * scale[i]
```

Não clipar `x_scaled`. O firmware deve clipar apenas a saída final:

```c
soc_final = fmaxf(0.0f, fminf(1.0f, raw_model_output));
```

## Caminho de Inferência

```text
entrada com 6 floats em unidades canônicas
-> MinMax scale
-> Dense(64, ReLU)
-> Dense(32, ReLU)
-> Dense(1, linear)
-> clip para [0.0, 1.0]
-> soc_final
```

## Escopo de Validação

| Escopo | Status |
|---|---|
| Validação offline Python | Consolidada na linhagem V7C |
| Replay GOLDEN | PASS no V8B2 |
| Replay EXTENDED | PASS no V8B2 |
| Replay ANOMALY | PASS no V8B2 |
| Campo | Não validado |
| Produção | Não validada |

## Limitações

- O replay usa vetores controlados, não aquisição real de sensor.
- O modelo pode degradar fora do domínio de treino.
- Temperatura, corrente e tensão fora dos limites documentados exigem interpretação conservadora.
- O próximo estágio necessário é V8C com bancada real ou semi-real.
