# Estratégia de otimização científica offline

## Estágio atual

O SOC-EDGE tem como eixo principal o SOC Method B no pacote V8B2. O baseline
canônico público é a MLP `float32` V8B2, validada por replay embarcado na ESP32.
As etapas recentes adicionaram auditoria estrutural do pacote, benchmark de
logs embarcados, análise de footprint, simulação de quantização de pesos e um
header INT8 candidato. Esse candidato ainda não é firmware INT8 validado.

## Por que otimização offline agora

A etapa mais útil antes de alterar firmware é organizar a matriz científica de
decisão. Otimizar sem contratos de experimento tende a misturar melhoria real,
vazamento de validação e custo embarcado. A Fase 4A define frentes, métricas,
splits e claims permitidos para que futuras mudanças sejam comparáveis ao
baseline V8B2.

## SOC_q_cycle e Coulomb counting

O Method B usa throughput de corrente para construir uma referência física por
ciclo:

```text
q_Ah = integral acumulada de |I| * dt / 3600
soc_method_b = clip(1 - q_Ah / Q_cycle, 0, 1)
```

Isso se aproxima de uma leitura controlada por Coulomb counting por ciclo, mas
não deve ser descrito como SOC absoluto verdadeiro sem erro. A referência é
adequada para treino, replay e comparação offline quando as unidades e a
segmentação de ciclo são controladas.

## Risco de drift

O erro pode mudar por ciclo, célula, regime de corrente, temperatura e estado de
envelhecimento. Por isso a matriz exige métricas como `drift_by_cycle`,
`temporal_stability`, `p95_abs_error` e splits que separam ciclo, célula e
tempo. Random holdout só serve como baseline fraco.

## Features matemáticas

A tensão tende a carregar muito sinal para SOC em datasets controlados, mas isso
não basta para robustez temporal. Corrente deve entrar como integração,
throughput ou estatística de janela, não apenas como valor instantâneo. As
features candidatas incluem:

- carga acumulada por janela;
- energia acumulada por janela;
- slope de tensão em janela;
- estatísticas rolling leves;
- deltas temporais já consolidados no V8B2.

## Splits necessários

Os splits prioritários são temporal, por ciclo, por célula e
leave-one-cell-out. Eles reduzem validação fraca e tornam explícito quando o
modelo só está interpolando exemplos semelhantes. Replay embarcado continua
necessário para claims de paridade Python vs ESP32.

## Modelos

A MLP V8B2 permanece baseline porque já tem pacote embarcado, replay, auditoria
e benchmark. Uma MLP menor pode ser comparada por footprint. Uma 1D-CNN leve só
deve entrar quando houver janelas temporais bem definidas e custo embarcado
estimado. LSTM, GRU e Transformer não são prioridade na ESP32 clássica por
custo, complexidade e necessidade de validação mais ampla.

## Quantização

A quantização atual é offline. O header INT8 é candidato experimental e serve
como ponte para implementação futura. Nenhum resultado atual autoriza claim de
latência melhor, firmware INT8 validado ou produção.

## Anomalias

As regras físicas V8B2 são úteis para replay e para protocolos futuros. A
próxima evolução deve separar recall, falso positivo, severidade, persistência e
coerência temporal. Detecção de anomalia em cenário versionado não equivale a
diagnóstico operacional de falha real.

## Ponte para SOH

SOH continua trilha separada. Indicadores como capacidade efetiva por ciclo,
drift de erro e proxies de resistência podem preparar uma extensão futura, mas
não transformam o SOC V8B2 em diagnóstico de degradação, predição de vida útil
ou manutenção preditiva operacional.

## Claims por etapa

Claims permitidos nesta fase:

- matriz pública de otimização offline;
- contratos de avaliação para features, splits, modelos, quantização, anomalias
  e embarcado;
- preparação científica para próximas fases.

Claims proibidos:

- validado em campo;
- pronto para produção;
- firmware INT8 validado;
- sensor físico real validado no V8B2;
- operação 24/7 validada;
- SOH operacional resolvido;
- modelo definitivo.
