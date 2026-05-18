# Protocolo de Validação Embarcada

A validação embarcada é organizada em camadas. Cada camada só sustenta claims dentro do seu próprio escopo.

| Camada | Descrição | Status |
|---|---|---|
| Offline Python | Treino, validação estatística e exportação | Concluída para a linha V7C/V8B2 |
| Export/parity | Paridade entre Python e implementação embarcada | Validada no pacote V8B2 |
| Replay embarcado | Execução de vetores canônicos na ESP32 | V8B2 PASS |
| Bancada real/semi-real | Aquisição por sensor físico em ambiente controlado | Próximo estágio V8C |
| Campo | Operação em ambiente real | Não validado |
| Pré-produção | Escala, longa duração e repetibilidade | Não validado |

## Critérios Gerais

- Sem crash ou reset inesperado.
- Latência registrada por amostra.
- Heap e serial registrados.
- Paridade Python vs ESP32 reportada.
- Critérios PASS/FAIL definidos antes da execução.
