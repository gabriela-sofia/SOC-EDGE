# Organização do Repositório

Este repositório foi reorganizado para separar a camada científica, a camada embarcada, os dados locais e os artefatos públicos versionáveis.

## Estrutura Criada

| Área | Função |
|---|---|
| `docs/metodologia/` | Base científica do Method B, definição do alvo, evolução experimental e limites de claim |
| `docs/datasets/` | Registro dos datasets e seus papéis metodológicos |
| `docs/experimentos/` | Registro de experimentos, modelos leves e protocolo de anomalias |
| `docs/validacao_embarcada/` | Protocolo de validação, relatório V8B2, versões e próximos experimentos |
| `docs/handoff_esp32/` | Documentação pública curada do handoff ESP32 |
| `embedded/handoff_v8b2/` | Pacote V8B2 curado para execução e auditoria pública |
| `manifests/` | Registros versionáveis de datasets, experimentos e replay |
| `local_only/` | Orientação sobre materiais locais fora do Git |

## Camada Científica

A camada científica documenta a origem do Method B, a definição do alvo SOC, os datasets usados, a evolução experimental, a validação cross-domain, os modelos leves e os limites de interpretação dos resultados.

## Camada Embarcada

A camada embarcada contém firmware, headers, replay vectors, protocolo de validação, critérios PASS/FAIL e templates de retorno. A ESP32 executa apenas inferência.

## Handoff Público Curado

O material bruto de `handoff_esp32_v8b2_canonical/` foi preservado localmente. A versão pública curada foi copiada para `embedded/handoff_v8b2/` e documentada em `docs/handoff_esp32/`, removendo tom de mensagem privada e mantendo instruções técnicas.

## Fora do Git

Permanecem fora do Git: dados brutos, outputs massivos, zips, caches, modelos binários, logs longos, ambientes virtuais, instruções locais de ferramentas e pacotes históricos brutos. Esses itens são bloqueados por `.gitignore`.

## Dados Pesados

Dados pesados são representados por manifests, schemas e documentação. Arquivos CSV pequenos são aceitos apenas quando atuam como replay, anomalia, manifest ou exemplo pequeno.

## Riscos Pendentes

- Revisar continuamente documentos antigos antes de torná-los públicos.
- Confirmar que nenhuma documentação pública menciona ferramentas locais de apoio.
- Rodar testes antes do primeiro commit.
- Conferir manualmente qualquer CSV novo antes de versionar.

## Comandos Antes do Primeiro Commit

```powershell
python -m pytest
git status --short
git diff --stat
git diff -- .gitignore README.md PROJECT_STATUS.md docs/ manifests/ embedded/ scripts/ src/ tests/
```
