# Critérios PASS/FAIL

## PASS

- Todas as amostras esperadas foram processadas.
- O SOC final está em `[0, 1]`.
- A paridade com referência Python está dentro do limiar definido no pacote.
- A latência está dentro do critério do protocolo.
- Não há crash ou reset inesperado.
- Heap e serial permanecem estáveis.
- Flags de anomalia batem com o esperado para o modo `ANOMALY`.

## FAIL

- Crash, reset inesperado ou travamento.
- Amostras ausentes.
- Divergência numérica acima do limiar.
- SOC fora de `[0, 1]` após pós-processamento.
- Logs incompletos ou corrompidos sem justificativa.
- Flags de anomalia incompatíveis com o manifest.

## WARN

`WARN` pode indicar execução parcial de modos, parse warning não bloqueante ou cenário esperado de saturação. Deve ser explicado no relatório e não pode ser convertido automaticamente em PASS global.
