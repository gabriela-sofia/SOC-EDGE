# Próximos Experimentos

O próximo estágio é V8C: validação de bancada com aquisição real ou semi-real.

## Objetivo V8C

Avaliar se o pipeline mantém comportamento coerente quando alimentado por sensor físico e descarga controlada, em vez de replay estático.

## Requisitos

- ESP32 com sensor de corrente/tensão real.
- Bateria e carga controlada.
- Log serial contínuo.
- Registro de latência, heap, flash e resets.
- Comparação com referência física disponível.
- Relatório de limitações.

## Saída Esperada

- CSV de aquisição.
- Relatório de execução.
- Análise de paridade e estabilidade.
- Decisão PASS/FAIL para avanço a piloto de campo.
