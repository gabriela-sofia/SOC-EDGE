# Experimentos com MLP Edge

O modelo de interesse é um MLP compacto, adequado para inferência embarcada. A seleção considera:

- baixo número de parâmetros;
- latência submilissegundo no replay V8B2;
- scaler reproduzível;
- ordem de features fixa;
- exportação simples para C/C++.

O treino é feito offline em Python. A ESP32 recebe apenas os parâmetros necessários para inferência.

O pacote V8B2 consolidou a execução do modelo canônico em replay embarcado, mas não substitui bancada com sensor real.
