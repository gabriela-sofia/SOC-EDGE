# Plano de Fault Injection

Fault injection testa respostas do sistema a falhas controladas de aquisição e comunicação.

## Cenários Planejados

| Cenário | Descrição | Resultado esperado |
|---|---|---|
| `sensor_dropout` | Sensor deixa de reportar por janela definida | Flag, log e recuperação ou FAIL explícito |
| `pacote_corrompido` | Linha serial incompleta ou campo inválido | Rejeição ou marcação da amostra |
| `reconexao_serial` | Interrupção e retomada de captura serial | Retomada sem claim indevido |
| `corrente_fora_unidade` | Corrente em escala incompatível | Detecção de unidade suspeita |
| `timestamp_nao_monotonico` | Timestamp retrocede ou repete | Flag de integridade temporal |
| `heap_critico` | Memória abaixo de limiar definido | WARN ou FAIL conforme severidade |
| `watchdog_timeout` | Execução bloqueada além do limite | Reset controlado e registro do evento |

## Limites

Estes testes verificam robustez de engenharia. Eles não validam campo, produção ou SOH.

## Registro

Cada cenário deve registrar entrada, evento injetado, resposta esperada, resposta observada, status e evidência.
