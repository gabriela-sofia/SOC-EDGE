# Mapa de Arquivos — Handoff V8B2 ESP32

Este documento descreve a estrutura do ZIP e o propósito de cada pasta/arquivo.

---

## Estrutura do ZIP

```
SOC_EDGE_V8B2_ESP32_HANDOFF/
│
├─ [Documentação do Handoff]
├── README.md                          Guia principal (comece aqui)
├── CHECKLIST_EXECUCAO.md              Checklist de progresso
├── RESULTADOS_ESPERADOS.md            Critérios e valores esperados
├── TEMPLATE_RETORNO_OPERADOR.md       Template de retorno
├── MAPA_ARQUIVOS.md                   Este arquivo
├── LIMITES_DE_CLAIM.md                Escopo permitido e proibido
├── TROUBLESHOOTING.md                 Problemas comuns e soluções
├── COMANDOS_VALIDACAO_LOCAL.md        Comandos para executar localmente
│
├─ [Firmware e Modelo]
├── firmware/
│   └── firmware_soc_v8b2_canonical.ino    Código principal ESP32
├── include/
│   ├── canonical_model_weights_v8b2.h     Pesos do modelo MLP (float32)
│   └── replay_vectors_v8b2.h              Dados de replay (GOLDEN/EXTENDED/ANOMALY)
│
├─ [Replay e Cenários]
├── replay/
│   ├── canonical_golden_vectors_v8b2.csv          Dados GOLDEN (~20 amostras)
│   ├── canonical_extended_replay_v8b2.csv         Dados EXTENDED (~120 amostras)
│   ├── canonical_extended_reference_v8b2.csv      Referência para validação
│   └── canonical_saturation_cases_v8b2.csv        Casos extremos
├── anomaly/
│   ├── anomaly_replay_scenarios_v8b2.csv          Cenários injetados (~10)
│   ├── anomaly_expected_flags_v8b2.csv            Flags esperadas
│   └── anomaly_manifest_v8b2.csv                  Manifest de tipos de anomalia
│
├─ [Validação e Manifests]
├── validation/
│   └── validate_esp32_v8b2.py                     Script de validação (canônico)
├── manifests/
│   ├── MODEL_MANIFEST_V8B2.md                     Especificação do modelo
│   └── canonical_replay_manifest_v8b2.csv         Manifest de replay
│
├─ [Resultados de Referência]
├── results_golden/
│   ├── v8b2_validation_metrics.json               Métricas GOLDEN
│   ├── v8b2_validation_report.md                  Relatório GOLDEN
│   └── v8b2_golden_comparison.csv                 Comparação esperado vs real
├── results_extended/
│   ├── v8b2_validation_metrics.json               Métricas EXTENDED
│   ├── v8b2_validation_report.md                  Relatório EXTENDED
│   └── v8b2_extended_comparison.csv               Comparação
├── results_anomaly/
│   ├── v8b2_validation_metrics.json               Métricas ANOMALY
│   ├── v8b2_validation_report.md                  Relatório ANOMALY
│   └── v8b2_anomaly_comparison.csv                Comparação flags
├── results_template/
│   └── RESULT_TEMPLATE_ESP32_V8B2_CANONICAL.md    Template para seus resultados
│
├─ [Logs de Referência]
├── v8b2_esp32_golden_log.txt                      Log de referência GOLDEN
├── v8b2_esp32_extended_log.txt                    Log de referência EXTENDED
├── v8b2_esp32_anomaly_log.txt                     Log de referência ANOMALY
│
├─ [Scripts de Validação]
├── scripts/
│   ├── validate_returned_logs.py                  Validador Python (principal)
│   └── validate_returned_logs.ps1                 Wrapper PowerShell (Windows)
│
├─ [Quantização Candidata — Apenas Referência]
├── quantization_candidate/
│   ├── README.md                                  Descrição (offline, não validado)
│   ├── V8B2_INT8_CANDIDATE_MANIFEST.json          Manifest de schema
│   └── canonical_model_weights_v8b2_int8_candidate.h   Pesos INT8 candidatos
│
├─ [Template de Retorno]
└── return_package_template/
    ├── README_DEVOLUCAO.md                        Instruções de retorno
    ├── ambiente_esp32_template.md                 Template dados de hardware
    ├── resultados_execucao_template.md            Template de resultados
    ├── observacoes_operador_template.md           Template de observações
    └── logs/
        ├── .gitkeep                               (placeholder)
        └── [seus logs vêm aqui]
```

---

## Descrição Detalhada por Pasta

### 📋 Documentação do Handoff

| Arquivo | Propósito | Quando ler |
|---------|-----------|-----------|
| **README.md** | Guia principal; objetivos, pré-requisitos, passos | **Primeiro** |
| **CHECKLIST_EXECUCAO.md** | Checklist de progresso; use para acompanhar | Antes de começar |
| **RESULTADOS_ESPERADOS.md** | Valores esperados de latência, heap, anomalias | Durante execução |
| **TEMPLATE_RETORNO_OPERADOR.md** | Template para preencher com seus dados | Após execução |
| **MAPA_ARQUIVOS.md** | Este arquivo; descrição da estrutura | Se tiver dúvida sobre arquivos |
| **LIMITES_DE_CLAIM.md** | O que é/não é permitido afirmar | Antes de comunicar resultados |
| **TROUBLESHOOTING.md** | Problemas comuns e soluções | Se algo falhar |
| **COMANDOS_VALIDACAO_LOCAL.md** | Exemplos de linha de comando | Ao executar validação |

### 🔧 Firmware e Modelo

| Arquivo | Conteúdo | Uso |
|---------|----------|-----|
| **firmware_soc_v8b2_canonical.ino** | Código principal ESP32 em C++ | Abrir em Arduino IDE / PlatformIO e compilar |
| **canonical_model_weights_v8b2.h** | Array de pesos MLP (float32) | Incluído automaticamente pelo .ino |
| **replay_vectors_v8b2.h** | Dados brutos de entrada (GOLDEN/EXTENDED/ANOMALY) | Incluído automaticamente pelo .ino |

**Como usar:**
1. Abra `firmware/firmware_soc_v8b2_canonical.ino` em sua IDE.
2. Certifique-se de que `include/` está no caminho do projeto.
3. Compile e upload.

### 📊 Replay e Cenários

| Arquivo | Conteúdo | Propósito |
|---------|----------|-----------|
| **canonical_golden_vectors_v8b2.csv** | ~20 amostras de entrada validadas | Replay rápido de teste |
| **canonical_extended_replay_v8b2.csv** | ~120 amostras variadas | Teste maior de estabilidade |
| **canonical_extended_reference_v8b2.csv** | Valores esperados para EXTENDED | Comparação |
| **canonical_saturation_cases_v8b2.csv** | Casos extremos (min/max bateria) | Teste de limites |
| **anomaly_replay_scenarios_v8b2.csv** | ~10 amostras com anomalias injetadas | Teste de detecção |
| **anomaly_expected_flags_v8b2.csv** | Flags esperadas para cada amostra | Validação |
| **anomaly_manifest_v8b2.csv** | Descrição de cada tipo de anomalia (ID, threshold, descrição) | Entender o que é testado |

**Importante:** Estes dados estão embutidos no header `replay_vectors_v8b2.h` durante compilação.

### ✓ Validação e Manifests

| Arquivo | Conteúdo | Uso |
|---------|----------|-----|
| **validate_esp32_v8b2.py** | Script canônico de validação | Referência; não é usado no handoff |
| **MODEL_MANIFEST_V8B2.md** | Especificação técnica do modelo | Leitura opcional para entender o modelo |
| **canonical_replay_manifest_v8b2.csv** | Manifest de replays | Referência |

### 📈 Resultados de Referência

Estes arquivos contêm resultados já validados em laboratório. **Use como referência** para comparar seus resultados:

| Pasta | Conteúdo |
|-------|----------|
| **results_golden/** | Métricas, relatório e comparação para GOLDEN |
| **results_extended/** | Métricas, relatório e comparação para EXTENDED |
| **results_anomaly/** | Métricas, relatório e comparação para ANOMALY |
| **results_template/** | Template para estruturar seus resultados |

Exemplo de comparação:
- Seu `latency_mean` deve estar próximo ao valor em `results_golden/v8b2_golden_comparison.csv`.
- Se diferir muito, consulte TROUBLESHOOTING.md.

### 📝 Logs de Referência

Logs brutos de referência já parseados:
- `v8b2_esp32_golden_log.txt`
- `v8b2_esp32_extended_log.txt`
- `v8b2_esp32_anomaly_log.txt`

**Formato esperado:**
```
sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status
1,GOLDEN,0.855,0.164,351068,351068,12288,0,0,OK
2,GOLDEN,0.856,0.165,351068,351068,12288,0,0,OK
...
```

### 🔍 Scripts de Validação

| Arquivo | Linguagem | Uso |
|---------|-----------|-----|
| **validate_returned_logs.py** | Python | Execute após coletar seus logs; parseia, calcula métricas, retorna JSON/CSV |
| **validate_returned_logs.ps1** | PowerShell | Wrapper Windows; chama o Python |

**Exemplo de uso:**
```bash
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt \
    --json v8b2_benchmark_summary.json
```

### 🔢 Quantização Candidata

**Importante:** INT8 é apenas um candidato offline. Não é firmware embarcado validado.

| Arquivo | Conteúdo |
|---------|----------|
| **README.md** | Descrição do experimento de quantização |
| **V8B2_INT8_CANDIDATE_MANIFEST.json** | Schema de quantização (per-array, symmetric) |
| **canonical_model_weights_v8b2_int8_candidate.h** | Pesos INT8 candidatos (~2.5 KB vs ~10 KB float32) |

**Não inclua isso em seu relatório operacional.** É apenas referência experimental.

### 📦 Template de Retorno

Sua pasta de retorno deve seguir esta estrutura:

```
retorno_v8b2_esp32/
├── ambiente_esp32.md                  [você preenche]
├── resultados_execucao.md             [você preenche]
├── observacoes_operador.md            [você preenche]
├── v8b2_benchmark_summary.json        [gerado pelo script]
├── v8b2_benchmark_metrics.csv         [gerado pelo script]
└── logs/
    ├── v8b2_esp32_golden_log.txt      [você salva]
    ├── v8b2_esp32_extended_log.txt    [você salva]
    └── v8b2_esp32_anomaly_log.txt     [você salva]
```

---

## Fluxo de Uso Recomendado

```
1. Extrait o ZIP
   ↓
2. Leia: README.md
   ↓
3. Confira: CHECKLIST_EXECUCAO.md (marque conforme avança)
   ↓
4. Abra: firmware/firmware_soc_v8b2_canonical.ino
   ↓
5. Compile e upload
   ↓
6. Execute: GOLDEN → EXTENDED → ANOMALY
   ↓
7. Salve logs em: return_package_template/logs/
   ↓
8. Execute: python scripts/validate_returned_logs.py
   ↓
9. Preencha: return_package_template/ambiente_esp32_template.md
                return_package_template/resultados_execucao_template.md
                return_package_template/observacoes_operador_template.md
   ↓
10. Mova preenchidos para: retorno_v8b2_esp32/
   ↓
11. Compacte: retorno_v8b2_esp32/ → ZIP
   ↓
12. Envie para coordenador
```

---

## Referência Rápida

- **Complicações com compilação?** → TROUBLESHOOTING.md
- **Serial não funciona?** → TROUBLESHOOTING.md
- **Valores fora do esperado?** → RESULTADOS_ESPERADOS.md
- **Linha de comando?** → COMANDOS_VALIDACAO_LOCAL.md
- **O que posso afirmar?** → LIMITES_DE_CLAIM.md

---

**Versão:** V8B2 · 2026-05-19
