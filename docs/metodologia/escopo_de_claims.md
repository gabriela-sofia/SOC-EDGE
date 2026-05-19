# Escopo de Claims

## Claims Permitidos

- O Method B define um alvo SOC por throughput acumulado de corrente e normalização por ciclo.
- O SOC Method B é o pipeline principal consolidado no pacote V8B2.
- O modelo canônico V7C foi executado dentro do pacote V8B2.
- O pacote V8B2 foi validado por replay embarcado na ESP32.
- GOLDEN, EXTENDED e ANOMALY passaram no escopo V8B2.
- A latência média reportada por modo ficou em torno de 0,2 ms ou abaixo.
- Paridade Python vs ESP32 pode ser afirmada apenas no escopo dos vetores versionados.
- A ESP32 executa inferência; treino permanece em Python.
- V8C é o próximo protocolo de bancada.

## Claims Não Permitidos

- Validado em campo.
- Pronto para produção.
- Modelo definitivo.
- Validado com sensores físicos reais no V8B2.
- Operação 24/7 validada.
- SOH operacional.
- Diagnóstico real de degradação.
- Predição de vida útil.
- Manutenção preditiva operacional.
- Validação industrial.
- Equivalente a coulomb counter de referência.

## Formulação Recomendada

> O modelo canônico V7C foi executado dentro do pacote V8B2, e o pacote V8B2 foi validado por replay embarcado na ESP32. O próximo passo metodológico é V8C, com aquisição real ou semi-real em bancada.
