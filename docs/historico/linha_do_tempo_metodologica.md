# Linha do Tempo Metodológica

Este documento consolida a linhagem histórica do SOC-EDGE a partir dos relatórios locais e documentos de trabalho ainda não publicados integralmente.

## Sequência Consolidada

| Fase | Papel metodológico | Estado público |
|---|---|---|
| Definição inicial do alvo | Formalização do `soc_method_b` por throughput acumulado | Consolidado em `docs/metodologia/definicao_alvo_soc.md` |
| Stage 4C | Validação histórica em ambiente Python e referência experimental inicial | Histórico, não é o estado atual |
| Stage 4D | Caminho histórico de deploy Keras/TFLite/ESP32 | Histórico, não é o estado atual |
| V6 | Paridade offline e preparação para exportação embarcada | Evidência intermediária |
| V7/V7B | Primeiros pacotes de handoff e replay embarcado | Evidência legada |
| V7C | Modelo canônico usado como base do V8B2 | Base técnica atual |
| V8A | Validação embarcada legada por replay | Evidência predecessora |
| V8B0/V8B1 | Expansão, recuperação canônica e preparação do pacote | Transição para V8B2 |
| V8B2 | Replay embarcado canônico na ESP32 | Estado consolidado atual |
| V8C | Bancada com aquisição real ou semi-real | Próximo estágio |

## Interpretação Conservadora

O histórico mostra progresso real de metodologia, exportação e replay embarcado. Ele não autoriza claims de campo, produção ou validação industrial.

## Materiais Ainda Locais

Os arquivos em `REPORTS/` e documentos soltos da raiz permanecem como fonte histórica local até curadoria individual. Eles não devem ser publicados integralmente sem revisão de linguagem, redundância e escopo de claims.
