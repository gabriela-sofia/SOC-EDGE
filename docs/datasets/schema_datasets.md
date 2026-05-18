# Schema de Datasets

O schema canônico mínimo para Method B deve preservar as seguintes colunas ou equivalentes rastreáveis:

| Campo | Unidade | Observação |
|---|---|---|
| `voltage_v` | V | Tensão medida ou normalizada para volts |
| `temperature_c` | Celsius | Temperatura em graus Celsius |
| `current_ma` | mA | Corrente obrigatoriamente em miliampere |
| `delta_voltage` | V | Diferença em relação à amostra anterior |
| `delta_temperature` | Celsius | Diferença em relação à amostra anterior |
| `delta_current` | mA | Diferença em relação à amostra anterior |
| `soc_method_b` | [0, 1] | Alvo derivado pelo Method B |

Qualquer conversão de unidade deve ser documentada antes do treino ou da validação.
