# Backlog de otimização SOC-EDGE

## Fase 4A: matriz científica de otimização

Objetivo: criar registries, schemas, métricas e auditores públicos para guiar a
otimização offline.

Arquivos previstos: registries em `experiments/`, scripts em
`scripts/offline_eval/` e documentação em `docs/`.

Critérios de aceite: registries parseáveis, IDs únicos, frentes obrigatórias
presentes e testes verdes.

Claim permitido: matriz auditável de planejamento científico.

Claim proibido: melhoria de modelo ou validação embarcada nova.

## Fase 4B: features matemáticas de janela/ciclo

Objetivo: implementar features leves de carga, energia, slope e estatísticas de
janela.

Arquivos previstos: scripts de geração offline, schemas de features e testes.

Critérios de aceite: features reproduzíveis e sem vazamento temporal.

Claim permitido: features candidatas para avaliação offline.

Claim proibido: robustez de campo ou ganho embarcado sem teste.

## Fase 4C: splits robustos célula/ciclo/tempo

Objetivo: padronizar splits temporal, por ciclo, por célula e leave-one-cell-out.

Arquivos previstos: geradores de split, manifests e testes de vazamento.

Critérios de aceite: splits determinísticos e auditáveis.

Claim permitido: avaliação offline mais conservadora.

Claim proibido: generalização universal.

## Fase 4D: baseline models offline

Objetivo: comparar MLP V8B2 com MLP menor, Ridge, Random Forest offline e
possível 1D-CNN leve.

Arquivos previstos: scripts de avaliação, manifests de modelos e relatórios
locais em `local_runs/`.

Critérios de aceite: métricas comparáveis contra o baseline V8B2.

Claim permitido: comparação offline controlada.

Claim proibido: modelo definitivo ou embarcado sem replay.

## Fase 4E: fixed-point reference

Objetivo: criar referência numérica fixed-point comparável ao float32.

Arquivos previstos: scripts de simulação, testes de saturação e documentação.

Critérios de aceite: erro numérico reportado e limites claros.

Claim permitido: referência fixed-point offline.

Claim proibido: firmware fixed-point validado.

## Fase 4F: anomalias v2

Objetivo: ampliar protocolo de anomalias com coerência temporal, severidade,
persistência e falso positivo.

Arquivos previstos: cenários, métricas e templates de resultado.

Critérios de aceite: recall e falso positivo definidos por cenário.

Claim permitido: protocolo offline de anomalias.

Claim proibido: diagnóstico operacional real.

## Fase 4G: runtime replay/stream

Objetivo: preparar execução em replay e stream digital para V8C de bancada.

Arquivos previstos: scripts de parsing, templates de log e critérios de
latência, heap e serial.

Critérios de aceite: logs parseáveis e métricas estáveis.

Claim permitido: preparação para bancada.

Claim proibido: campo, produção ou operação 24/7.

## Fase 4H: SOH extension protocol

Objetivo: estruturar a trilha futura de SOH sem incorporá-la ao claim SOC V8B2.

Arquivos previstos: protocolo, métricas de drift, capacidade efetiva e proxies.

Critérios de aceite: escopo separado e claims limitados.

Claim permitido: prontidão metodológica para extensão SOH.

Claim proibido: predição de vida útil ou manutenção preditiva operacional.
