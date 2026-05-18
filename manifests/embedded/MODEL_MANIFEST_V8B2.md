# Manifest do Modelo V8B2

Este arquivo espelha o manifest público curado de `embedded/handoff_v8b2/manifests/MODEL_MANIFEST_V8B2.md`.

Resumo:

- modelo base: V7C canonical;
- alvo: `soc_method_b`;
- entrada canônica: `[voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current]`;
- scaler: MinMax compatível com sklearn;
- regra crítica: não clipar features escaladas;
- clip apenas no SOC final;
- status atual: replay embarcado V8B2 PASS;
- próximo estágio: V8C bancada real ou semi-real.
