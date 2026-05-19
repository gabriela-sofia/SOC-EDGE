# Resultados Públicos

Este arquivo resume apenas resultados públicos sustentados pelos artefatos versionados do SOC-EDGE.

## SOC Method B

O pipeline principal do repositório é o SOC Method B para inferência embarcada em ESP32.

O modelo canônico V7C foi executado dentro do pacote V8B2, e o pacote V8B2 foi validado por replay embarcado na ESP32.

| Item | Resultado | Evidência pública |
|---|---|---|
| GOLDEN | PASS | `embedded/handoff_v8b2/replay/` e protocolo V8B2 |
| EXTENDED | PASS | `embedded/handoff_v8b2/replay/` e protocolo V8B2 |
| ANOMALY | PASS | `embedded/handoff_v8b2/anomaly/` e protocolo V8B2 |
| Paridade Python vs ESP32 | Limitada aos vetores versionados | `embedded/handoff_v8b2/validation/validate_esp32_v8b2.py` |

## SOH

SOH é uma trilha separada de preparação metodológica. Ela não integra o pacote SOC V8B2 e não possui, neste repositório público, validação operacional de degradação real, manutenção preditiva ou predição de vida útil.

Resultados de replay/paridade SOH só devem ser afirmados quando forem sustentados por artefatos públicos versionados e devem permanecer restritos ao escopo desses artefatos.

## Limites

Os resultados atuais não validam campo, produção, sensor físico real no V8B2, operação 24/7 ou validação industrial.
