# Status do Projeto SOC Method B

Atualizado em: 2026-05-19

## Estágio Atual

O SOC Method B é o pipeline principal do repositório. O projeto está no estágio V8B2 consolidado. O modelo canônico V7C foi executado dentro do pacote V8B2, e o pacote V8B2 validou a inferência embarcada por replay na ESP32, usando vetores controlados e protocolo de anomalias.

## Validado

| Item | Status | Evidência |
|---|---|---|
| Replay GOLDEN | PASS | 20 amostras canônicas executadas sem erro bloqueante |
| Replay EXTENDED | PASS | 120 amostras representativas executadas no pacote V8B2 |
| Replay ANOMALY | PASS | 10 cenários canônicos detectados no protocolo V8B2 |
| Resultado consolidado | Overall PASS | Três modos aprovados em execução embarcada por replay |
| Inferência na ESP32 | Validada por replay | Firmware V8B2 executou o modelo canônico |
| Latência | Reportada em torno de 0,2 ms ou abaixo por modo | Critério de replay atendido |
| Heap e serial | Estáveis nos replays reportados | Sem crash/reset inesperado consolidado |

## Parcialmente Validado

| Item | Situação |
|---|---|
| Paridade Python vs ESP32 | Validada no contexto dos vetores e logs V8B2; deve ser repetida a cada novo pacote |
| Protocolo de anomalias | Validado em replay sintético isolado; ainda não cobre sensor físico real |
| Generalização cross-domain | Documentada como etapa metodológica; não deve ser confundida com campo |

## Ainda Não Validado

| Item | Motivo |
|---|---|
| Validação em campo | Não há piloto operacional real documentado após V8B2 |
| Produção | Faltam bancada real, campo, longa duração, repetibilidade de hardware e critérios de escala |
| Sensor físico real | V8B2 usou replay; V8C deve usar aquisição real ou semi-real |
| SOH operacional | SOH não integra o pacote SOC V8B2 e não possui validação operacional de degradação em campo |
| Robustez 24/7 | Não foi validada como operação contínua longa |

## Limites de Claim

Claim público permitido:

> O pacote V8B2 foi validado por replay embarcado na ESP32, com GOLDEN, EXTENDED e ANOMALY em PASS.

Claims que não devem ser usados:

- validado em campo;
- pronto para produção;
- modelo definitivo;
- validação com sensor físico real no V8B2;
- operação contínua de longa duração validada;
- manutenção preditiva operacional;
- diagnóstico real de degradação;
- predição de vida útil.

## Trilha SOH

SOH permanece uma trilha separada de preparação metodológica. Ela pode orientar futuros experimentos, mas não altera o claim SOC V8B2 e não deve ser usada para afirmar degradação real, vida útil, campo ou produção.

## Próximo Experimento

O próximo passo é V8C: validação de bancada com aquisição real ou semi-real.

Requisitos mínimos esperados:

- ESP32 com sensor de corrente/tensão real, como INA219 ou equivalente;
- bateria Li-ion e carga controlada;
- log serial com timestamp, tensão, temperatura, corrente, SOC, latência e heap;
- relatório de RAM, flash, latência e estabilidade;
- comparação pós-teste com referência física disponível;
- análise explícita de falhas, resets, perda de serial e drift.
