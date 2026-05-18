# Protocolo V8C de Bancada

O V8C é o próximo estágio após o replay embarcado V8B2. Seu objetivo é avaliar o pipeline SOC Method B com aquisição real ou semi-real em bancada, usando sensor físico e descarga controlada.

## Objetivo

Verificar se a inferência embarcada permanece estável quando alimentada por leituras reais de tensão, temperatura e corrente ao longo do tempo.

## Escopo

V8C cobre bancada controlada. Não cobre campo, produção, validação industrial ou operação longa em ambiente real.

## Hardware Mínimo

- ESP32 compatível com o firmware do projeto.
- Sensor de tensão/corrente, como INA219 ou equivalente.
- Fonte ou bateria Li-ion real.
- Carga controlada, como resistor ou carga eletrônica.
- Computador para captura serial.
- Instrumento externo de conferência, quando disponível.

## Aquisição

Cada amostra deve registrar:

- `timestamp_ms`;
- `voltage_v`;
- `temperature_c`;
- `current_ma`;
- `delta_voltage`;
- `delta_temperature`;
- `delta_current`;
- `soc_final`;
- `inference_time_ms`;
- `free_heap`;
- `min_free_heap`;
- `reset_count`;
- `anomaly_flag`;
- `status`.

## Execução

1. Registrar identificação do hardware.
2. Verificar calibração básica do sensor.
3. Iniciar captura serial antes da descarga.
4. Executar aquisição contínua por período definido.
5. Registrar qualquer reset, perda de serial ou falha de sensor.
6. Salvar log bruto e relatório resumido.
7. Validar integridade do log antes de interpretar resultados.

## Saídas Esperadas

- log serial bruto;
- CSV de aquisição;
- relatório de hardware;
- relatório PASS/WARN/FAIL;
- gráfico ou tabela de coerência temporal, quando disponível.
