# Protocolo V8C: quantizacao e benchmark justo na ESP32

## Escopo

Este protocolo define a Fase 2 experimental do SOC-EDGE: comparar a MLP float V8B2, ja validada por replay embarcado na ESP32, com uma candidata quantizada ou compactada. A etapa existe para medir custo embarcado versus erro de paridade, sem alterar o alvo Method B / `soc_q_cycle` e sem substituir o pacote V8B2.

A MLP float V8B2 continua sendo o baseline canonico. Qualquer versao INT8, dequantizada, compactada ou menor e candidata experimental ate passar pelos mesmos vetores, pelo mesmo contrato de entrada e pelas mesmas metricas.

## Objetivo

O objetivo e produzir evidencia comparavel sobre custo embarcado, erro numerico e paridade Python versus ESP32 para uma candidata experimental, mantendo a MLP float V8B2 como referencia.

## Motivacao

Depois do replay V8B2 validado, a pergunta tecnica passa a ser se existe uma representacao mais barata para a ESP32. Quantizacao ou compactacao podem reduzir memoria, flash e tempo de inferencia, mas tambem podem introduzir erro numerico. Por isso, a comparacao deve ser auditavel e sempre ancorada no baseline float.

Esta fase nao reabre a metodologia do alvo. O alvo principal permanece Method B / `soc_q_cycle`, e a ESP32 permanece apenas como ambiente de inferencia.

## Contrato fixo

- Modelo baseline: MLP V7C/V8B2 float.
- Arquitetura baseline: `Input(6) -> Dense(64, ReLU) -> Dense(32, ReLU) -> Dense(1, linear)`.
- Parametros baseline: 2.561.
- Ordem obrigatoria das features: `voltage_v`, `temperature_c`, `current_ma`, `delta_voltage`, `delta_temperature`, `delta_current`.
- `current_ma` e `delta_current` sao sempre em mA.
- O scaler deve seguir a politica conceitual do `sklearn.MinMaxScaler`.
- Features escaladas nao devem ser clipadas.
- Apenas o SOC final deve ser clipado para `[0, 1]`.

## Benchmark justo

Um benchmark justo entre float e candidata exige:

- os mesmos vetores GOLDEN, EXTENDED e ANOMALY usados no V8B2;
- a mesma ordem canonica de features;
- a mesma unidade de corrente em mA;
- a mesma politica de scaler;
- o mesmo target Method B / `soc_q_cycle`;
- a mesma regra de clipping somente no SOC final;
- metricas calculadas de forma comparavel para baseline e candidata;
- logs ESP32 com campos suficientes para medir paridade, latencia e memoria.

## Limites de claim

O unico claim herdado do baseline e: validado por replay embarcado na ESP32. A candidata quantizada ou compactada deve ser descrita como experimental ate que seus logs sejam avaliados.

Este protocolo nao significa que ha validacao em campo, nao significa que esta pronto para producao, nao significa que ha sensor fisico real validado, nao significa que ha operacao 24/7 validada, nao significa que ha SOH operacional e nao significa que ha diagnostico real de degradacao.
