# Handoff V8B2 Curado

Este pacote contém a versão pública curada do handoff V8B2 para replay embarcado na ESP32.

## Conteúdo

```text
firmware/          firmware principal
include/           pesos, scaler e vetores compiláveis
replay/            vetores GOLDEN, EXTENDED e saturação
anomaly/           cenários e flags esperadas
validation/        validador Python dos logs
manifests/         manifests de modelo e replay
results_template/  template de retorno
```

## Escopo

O pacote valida replay embarcado. Ele não valida campo, produção, sensor físico real ou operação contínua longa.

## Documentação

Consultar `docs/handoff_esp32/` para protocolo de execução, critérios PASS/FAIL e templates de retorno.
