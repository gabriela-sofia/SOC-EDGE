# Base Científica do Method B

O Method B estima SOC por uma aproximação física baseada em throughput de corrente. O alvo é derivado de integração acumulada de corrente e normalização pelo throughput máximo do ciclo.

```text
q_Ah = integral acumulada de |I| * dt / 3600
Q_cycle = throughput máximo por ciclo
soc_method_b = clip(1 - q_Ah / Q_cycle, 0, 1)
```

O modelo leve aprende uma relação não linear entre observações pontuais e o alvo físico-estimado. O treinamento ocorre em Python; a ESP32 recebe apenas scaler, pesos e código de inferência.

## Entradas Canônicas

```text
[voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current]
```

Regras normativas:

- `current_ma` usa miliampere.
- A ordem das features é imutável.
- O scaler deve reproduzir o `MinMaxScaler` do Python.
- Features escaladas não são clipadas.
- O clip é aplicado apenas ao SOC final.

## Modelo

O pacote V8B2 usa um MLP compacto com seis entradas, duas camadas ocultas e uma saída escalar. A arquitetura é adequada para inferência embarcada leve e foi avaliada por replay na ESP32.

## Limites

O Method B não é equivalente a um coulomb counter de referência. Ele também não valida SOH, campo, produção, sensores reais ou longa duração apenas pelo replay V8B2.
