# Protocolo de Anomalias

O protocolo V8B2 avalia cenários sintéticos de anomalia por replay. Ele verifica se o firmware detecta ou sinaliza condições esperadas sem crash ou reset.

## Cenários Canônicos

1. `voltage_spike`
2. `current_spike`
3. `temperature_jump`
4. `voltage_flatline`
5. `current_dropout`
6. `noise_burst`
7. `soc_temporal_incoherence`
8. `domain_shift_current_scale`
9. `low_voltage_warning`
10. `high_temperature_warning`

## Limite de Interpretação

O protocolo valida replay sintético isolado. Falhas reais de sensor, ruído físico de bancada e operação contínua dependem do V8C e de etapas posteriores.
