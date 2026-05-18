# Histórico Experimental do SOC-EDGE

Este documento resume a evolução experimental sem publicar relatórios brutos.

## Trilhas Experimentais

| Trilha | Função | Situação |
|---|---|---|
| Normalização de datasets | Preparar domínios heterogêneos para Method B | Histórica |
| Validação cross-domain | Avaliar transferência entre Oxford, LG18650, SP2 e IoT | Histórica |
| Modelos leves | Selecionar arquitetura compatível com edge | Consolidada para V7C/V8B2 |
| Exportação embarcada | Transformar scaler e pesos em artefatos de firmware | Consolidada |
| Replay | Validar execução embarcada com vetores controlados | V8B2 PASS |
| Anomalias sintéticas | Avaliar regras controladas de fault injection | V8B2 PASS |

## Riscos Experimentais Registrados

- Corrente em unidade errada altera drasticamente a inferência.
- Clipping indevido de features escaladas quebra paridade.
- Replay não substitui aquisição real.
- Testes sintéticos de anomalia não substituem falhas reais de sensor.

## Uso Público

Este histórico deve ser usado para rastreabilidade científica, não para ampliar claims.
