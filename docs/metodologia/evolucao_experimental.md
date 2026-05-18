# Evolução Experimental

A linhagem metodológica do projeto pode ser resumida como:

```text
datasets de bateria
-> normalização e definição do Method B
-> validação cross-domain
-> experimentos com modelos leves
-> exportação de scaler e pesos
-> paridade Python vs firmware
-> pacote ESP32
-> replay embarcado
-> protocolo de anomalias
-> V8B2 Overall PASS
-> V8C bancada real
```

## Marcos

| Marco | Papel |
|---|---|
| Oxford | Referência laboratorial e base histórica do projeto |
| LG18650_HG2 | Domínio complementar para avaliação de perfis de bateria |
| SP2 | Domínio adicional para análise cross-domain |
| IoT | Domínio usado na consolidação canônica V7C/V8B2 |
| V7C | Modelo canônico e artefatos de exportação |
| V8B2 | Replay embarcado validado na ESP32 |
| V8C | Próximo estágio: bancada com aquisição real |

## Critério de Continuidade

Cada avanço deve preservar rastreabilidade: dataset, preprocessing, ordem de features, scaler, pesos, firmware, replay e relatório de validação.
