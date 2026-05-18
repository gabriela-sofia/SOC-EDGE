# Definição do Alvo SOC

O alvo oficial desta linha metodológica é `soc_method_b`.

## Formulação

```text
q_Ah = integral acumulada de |I| * dt / 3600
Q_cycle = throughput máximo por ciclo
soc_method_b = clip(1 - q_Ah / Q_cycle, 0, 1)
```

## Interpretação

`q_Ah` representa o throughput acumulado de corrente no ciclo. `Q_cycle` representa a escala de normalização do ciclo. O SOC resultante é limitado ao intervalo `[0, 1]`.

## Uso no Modelo

O modelo não calcula o alvo em tempo real. Ele aprende, em treino offline, uma aproximação do alvo a partir das seis features canônicas. Na ESP32, o firmware apenas executa o forward pass e aplica o clip final.

## Restrições

- Não tratar `soc_method_b` como ground truth físico universal.
- Não usar dados fora de unidade ou ordem canônica.
- Não clipar features escaladas antes da rede.
- Não afirmar validação fora do escopo experimental registrado.
