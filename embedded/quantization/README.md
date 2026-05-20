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
