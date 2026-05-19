# Registro de Claims

Este registro define quais claims são permitidos no estado público atual do SOC-EDGE e quais extrapolações devem ser evitadas.

| Claim permitido | Evidência pública | Limite | Claim proibido relacionado |
|---|---|---|---|
| SOC V8B2 validado por replay embarcado na ESP32 | `embedded/handoff_v8b2/`, `docs/validacao_embarcada/relatorio_v8b2.md` | Replay com vetores controlados | Validado em campo |
| GOLDEN, EXTENDED e ANOMALY em PASS no V8B2 | CSVs em `embedded/handoff_v8b2/replay/` e `embedded/handoff_v8b2/anomaly/` | Não substitui sensor físico real | Sensor físico real validado no V8B2 |
| Paridade Python vs ESP32 no escopo dos vetores versionados | `embedded/handoff_v8b2/validation/validate_esp32_v8b2.py` | Restrita ao schema e aos vetores versionados | Modelo definitivo ou validação industrial |
| O modelo canônico V7C foi executado dentro do pacote V8B2 | Manifest do modelo V8B2 | O claim público validado é do pacote V8B2 | V7C validado genericamente fora do pacote |
| SOH replay/paridade embarcada | Artefatos SOH públicos versionados, quando presentes | Não é SOH operacional nem degradação real | Diagnóstico real de degradação ou predição de vida útil |
| V8C é o próximo protocolo de bancada | `docs/validacao_embarcada/protocolo_v8c_bancada.md` | Planejamento de bancada, ainda não executado | Pronto para produção |
| SOH readiness existe como trilha separada | `docs/metodologia/soh_readiness.md` | Não é SOH operacional | Manutenção preditiva operacional |

## Claims Proibidos

- Validado em campo.
- Pronto para produção.
- Sensor físico real validado no V8B2.
- Operação 24/7 validada.
- Manutenção preditiva operacional.
- Diagnóstico real de degradação.
- Predição de vida útil.
- Modelo definitivo.
- Validação industrial.

## Formulação Recomendada

> O SOC Method B é o pipeline principal consolidado no pacote V8B2. O modelo canônico V7C foi executado dentro do pacote V8B2, e o pacote V8B2 foi validado por replay embarcado na ESP32 com GOLDEN, EXTENDED e ANOMALY em PASS.
