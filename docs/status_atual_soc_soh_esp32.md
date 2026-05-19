# Status Atual: SOC, SOH e ESP32

## SOC

SOC Method B é o pipeline principal do SOC-EDGE. O estado consolidado é V8B2: replay embarcado validado na ESP32 com GOLDEN, EXTENDED e ANOMALY em PASS.

O modelo técnico de base é o V7C canonical. A formulação pública deve ser:

> O modelo canônico V7C foi executado dentro do pacote V8B2, e o pacote V8B2 foi validado por replay embarcado na ESP32.

## SOH

SOH é uma trilha separada. Ela não integra o pacote SOC V8B2 e não deve ser usada para afirmar diagnóstico operacional de degradação, vida útil, campo ou produção.

Quando houver replay/paridade SOH sustentado por artefatos versionados, o claim deve permanecer restrito a replay e paridade embarcada, sem extrapolar para degradação real ou manutenção preditiva.

## ESP32

A ESP32 executa inferência e validação por replay no pacote V8B2. Ela não executa treino.

## Próximo Estágio

V8C é o próximo estágio: bancada com aquisição real ou semi-real, sensor físico, logs contínuos e avaliação de estabilidade temporal.
