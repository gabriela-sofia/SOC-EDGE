# SOH Readiness

Este documento prepara a evolução futura do SOC-EDGE para considerar degradação temporal. Ele não transforma o projeto atual em um sistema de SOH operacional.

## Escopo Atual

O foco atual permanece SOC Method B com inferência embarcada e validação progressiva. SOH é tratado como trilha separada de preparação conceitual e requisito futuro de dados. SOH não integra o pacote SOC V8B2 e não possui validação operacional de degradação em campo.

## Variáveis Potenciais

| Indicador | Papel possível | Status atual |
|---|---|---|
| Throughput acumulado | Proxy de uso energético total | Requer aquisição longitudinal |
| Número de ciclos | Indicador de envelhecimento | Não consolidado no pacote SOC V8B2 |
| Drift de tensão | Possível sinal de degradação | Requer controle de carga e temperatura |
| Drift de corrente | Pode indicar mudança operacional ou sensor | Precisa separar sensor de bateria |
| Temperatura acumulada | Estresse térmico ao longo do tempo | Requer logs longos confiáveis |
| Resistência interna estimada | Indicador físico de degradação | Não operacional no pacote SOC V8B2 |

## Dependências Futuras

- V8C com aquisição real ou semi-real.
- Logs contínuos com timestamps confiáveis.
- Registro de ciclos ou janelas equivalentes.
- Identificação de bateria, carga e sensor.
- Separação entre falha de sensor e degradação física.
- Referência externa ou protocolo de comparação para degradação.

## Limites Atuais

O projeto atual não afirma:

- SOH operacional;
- predição de vida útil;
- diagnóstico real de degradação;
- validação em bateria envelhecida;
- compensação automática por envelhecimento.

## Caminho Científico Possível

1. Consolidar V8C com aquisição real.
2. Estender logs para janelas longas.
3. Definir indicadores candidatos de degradação.
4. Auditar se os indicadores são físicos ou artefatos de sensor.
5. Criar protocolo separado de SOH, sem reescrever o Method B.

## Regra de Conservadorismo

SOH deve entrar como extensão futura, não como claim implícito do modelo SOC atual.
