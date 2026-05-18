# Documentos Históricos Curados

Este índice registra como os documentos históricos locais devem ser tratados antes de publicação.

## Grupos de Conteúdo

| Origem local | Destino público preferencial | Critério |
|---|---|---|
| `REPORTS/SOC_METHOD_B_SCIENTIFIC_BASE.md` | `docs/metodologia/` | Base conceitual e invariantes |
| `REPORTS/SOC_EMBEDDED_VALIDATION_PROTOCOL.md` | `docs/validacao_embarcada/` | Camadas de validação |
| `REPORTS/SOC_V8B2_RESULTS_REPORT.md` | `docs/validacao_embarcada/` | Estado V8B2 consolidado |
| `REPORTS/SOC_NEXT_EXPERIMENTS_ROADMAP.md` | `docs/validacao_embarcada/` | Próximos experimentos |
| `REPORTS/V8*.md` | `docs/historico/` e `docs/validacao_embarcada/` | Histórico de replay e handoff |
| `MEETING_*.md` | `docs/historico/` | Registro de alinhamento, sem tom privado |
| `*.txt` históricos | Markdown curado | Converter apenas se houver valor metodológico |

## Regras de Curadoria

- Remover linguagem de ferramenta, autoria automática e instruções internas de trabalho.
- Traduzir inglês desnecessário para português técnico.
- Preservar identificadores, nomes de scripts, nomes de arquivos e campos técnicos.
- Não criar claims novos.
- Marcar evidências antigas como históricas quando não forem o estado atual.
- Não publicar relatórios brutos que ainda contenham ruído ou redundância.

## Estado Atual da Curadoria

Nesta fase, o histórico foi consolidado em documentos públicos sintéticos. Os arquivos originais permanecem locais e não foram adicionados ao Git.
