# Replay offline embarcado

A validação embarcada foi feita por replay offline controlado.

O notebook gera features, scaler, referência Python e CSV de entrada.

A ESP32 aplica o scaler, executa o modelo e devolve `sample_id + inferência`.

No PC, o resultado é comparado contra a referência Python usando merge por `sample_id`.
