# Consolidação Científica Histórica

O SOC-EDGE evoluiu de experimentos de definição de alvo e validação cross-domain para um pacote embarcado com replay validado na ESP32.

## Elementos Consolidados

1. Definição do alvo `soc_method_b`.
2. Separação entre treino offline e inferência embarcada.
3. Ordem canônica das seis features.
4. Uso de scaler compatível com `sklearn`.
5. Paridade Python versus firmware como requisito.
6. Replay embarcado como etapa intermediária, não como campo.
7. Protocolo de anomalias sintéticas como teste controlado.
8. V8B2 como estado atual validado por replay.

## Limites Persistentes

- O projeto ainda não validou aquisição real de sensor em bancada.
- O projeto ainda não validou campo.
- O projeto ainda não está em produção.
- O projeto ainda não modela SOH operacionalmente.

## Valor do Histórico

O histórico é importante porque documenta decisões negativas e positivas: escolhas de features, riscos de unidade de corrente, necessidade de scaler idêntico, separação entre replay e bancada, e limites de claim.
