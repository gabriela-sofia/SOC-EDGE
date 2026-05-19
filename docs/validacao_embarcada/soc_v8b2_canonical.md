# SOC V8B2 Canonical

O pacote V8B2 é o estado público consolidado da validação SOC embarcada.

## Escopo Validado

- Replay embarcado na ESP32.
- GOLDEN PASS.
- EXTENDED PASS.
- ANOMALY PASS.
- Paridade Python vs ESP32 no escopo dos vetores versionados.

## Relação V7C/V8B2

O V7C canonical é o modelo técnico de base. O claim público validado deve se referir ao pacote V8B2:

> O modelo canônico V7C foi executado dentro do pacote V8B2, e o pacote V8B2 foi validado por replay embarcado na ESP32.

## Caminho Canônico do Validador

```powershell
python embedded/handoff_v8b2/validation/validate_esp32_v8b2.py --help
```

## Limites

V8B2 não valida bancada com sensor físico real, campo, produção, operação 24/7, manutenção preditiva ou diagnóstico real de degradação.
