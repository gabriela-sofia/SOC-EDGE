# SOH — validação embarcada ESP32

O SOH usa 16 features agregadas por ciclo.

Random Forest foi usado como benchmark tabular forte: R² ≈ 0.987.

A MLP foi escolhida como candidata embarcada: R² ≈ 0.91.

## Validação ESP32

- 120/120 amostras válidas
- sample_id_match_all = True
- MAE Python vs ESP32 ≈ 1e-6
- RMSE Python vs ESP32 ≈ 1e-6
- inferência média ≈ 0.255 ms
- heap mínimo ≈ 277204 bytes
