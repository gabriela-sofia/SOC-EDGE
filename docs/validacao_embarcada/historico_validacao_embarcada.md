# Histórico de Validação Embarcada

O caminho embarcado do SOC-EDGE avançou em camadas, até o estado V8B2.

## Marcos

| Marco | Descrição | Interpretação |
|---|---|---|
| Exportação inicial | Conversão de artefatos Python para execução embarcada | Preparação técnica |
| Paridade offline | Conferência de equivalência numérica fora do hardware | Porta de entrada para firmware |
| Handoff V7/V7B | Primeiros pacotes de execução e retorno | Evidência legada |
| V8A | Replay embarcado predecessor | Histórico |
| V8B0/V8B1 | Ajustes de pacote, anomalia e recuperação canônica | Transição |
| V8B2 | GOLDEN, EXTENDED e ANOMALY em PASS | Estado atual |

## Claim Atual

O claim atual permanece restrito:

> Replay embarcado V8B2 validado na ESP32.

## Próxima Lacuna

O V8C deve substituir vetores estáticos por aquisição real ou semi-real em bancada, registrando V/T/I reais, timestamps, latência, heap, resets e estabilidade temporal.
