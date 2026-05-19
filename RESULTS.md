# Resultados consolidados

## SOC — V8B2 Canonical ESP32

| Bloco | Status |
|---|---|
| GOLDEN | PASS |
| EXTENDED | PASS |
| ANOMALY | PASS |

Claim atual:

> O modelo canônico V7C foi validado em replay embarcado na ESP32, com paridade GOLDEN, replay EXTENDED e cenários ANOMALY controlados.

## SOH — ESP32 Replay

| Métrica | Resultado |
|---|---|
| Amostras válidas | 120/120 |
| sample_id_match_all | True |
| MAE Python vs ESP32 | ~1e-6 |
| RMSE Python vs ESP32 | ~1e-6 |
| Inferência média | ~0.255 ms |
| Heap mínimo | ~277204 bytes |
