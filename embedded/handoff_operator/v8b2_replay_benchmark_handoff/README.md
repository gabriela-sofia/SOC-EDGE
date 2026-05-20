# Handoff Operacional V8B2 — Replay e Benchmark ESP32

## Objetivo

Este pacote permite que você valide e execute o pipeline **V8B2 (Method B coulombic SOC)** em hardware ESP32, capturando métricas de latência, consumo de heap, uso de flash e estabilidade. O foco é **repetir e confirmar** os resultados de benchmark já obtidos em laboratório, em ambiente controlado.

## O que você vai fazer

1. Compilar o firmware canônico V8B2
2. Executar três replays (GOLDEN, EXTENDED, ANOMALY)
3. Coletar logs seriais e métricas
4. Validar localmente com scripts fornecidos
5. Preencher templates de retorno
6. Devolver a pasta de resultados compactada

## O que você vai devolver

Uma pasta `retorno_v8b2_esp32/` contendo:
- Logs brutos das três execuções (GOLDEN, EXTENDED, ANOMALY)
- Métricas em JSON e CSV
- Documento de ambiente (placa, versão do core, firmware usado)
- Documento de resultados (latência, heap, resets, anomalias)
- Observações operacionais

## Importantes limitações deste handoff

| Aspecto | O que NÃO é |
|---------|-----------|
| **Campo** | Este é teste embarcado, não validação de campo |
| **Produção** | V8B2 é baseline lab; não é firmware de produção |
| **V8C** | V8C é a próxima etapa; não está incluída aqui |
| **INT8 validado** | INT8 é candidato offline; não é firmware embarcado validado |
| **SOH operacional** | SOH é trilha separada |
| **Sensor físico** | Estamos usando stream/replay digital, não sensor real |
| **24/7** | Não validamos operação contínua |

## Resumo do artefato

```
SOC Method B (coulombic, scientifically defensible)
    ↓
MLP V8B2 (domain-specific, IoT optimized)
    ↓
Replay embarcado (GOLDEN / EXTENDED / ANOMALY)
    ↓
Latência, heap, flash, resets, estabilidade serial
```

## Pré-requisitos

- **Hardware:** ESP32 DevKit V1 ou equivalente clássico
- **Cabo USB:** Confiável (USB 2.0, baud rate 115200)
- **IDE:** Arduino IDE 1.8.19+ ou PlatformIO 6.0+
- **Python:** 3.10+, com pip (para validação local)
- **Acesso serial:** Capacidade de monitorar porta serialem tempo real
- **Espaço disco:** ~500MB para firmware, logs, temporários

## Passos principais

### 1. Preparação

```
1. Abra a pasta descompactada do handoff.
2. Confira o arquivo MAPA_ARQUIVOS.md para entender a estrutura.
3. Confirme o README.md em embedded/handoff_v8b2/firmware/.
```

### 2. Compilação

```
4. Abra embedded/handoff_v8b2/firmware/firmware_soc_v8b2_canonical.ino em sua IDE.
5. Selecione: ESP32 DevKit V1 (ou equivalente).
6. Compile (Sketch → Verify ou Build em PlatformIO).
7. Registre o valor de Flash usado (mostrado ao final da compilação).
8. Faça upload para a placa.
```

### 3. Execução GOLDEN

```
9. Abra o Serial Monitor (9600 baud se IDE, case-by-case em outros).
10. Digite: GOLDEN (enter).
11. Aguarde até receber [GOLDEN_END].
12. Salve os logs em: retorno_v8b2_esp32/logs/v8b2_esp32_golden_log.txt
```

### 4. Execução EXTENDED

```
13. Digite: EXTENDED (enter).
14. Aguarde até receber [EXTENDED_END].
15. Salve os logs em: retorno_v8b2_esp32/logs/v8b2_esp32_extended_log.txt
```

### 5. Execução ANOMALY

```
16. Digite: ANOMALY (enter).
17. Aguarde até receber [ANOMALY_END].
18. Salve os logs em: retorno_v8b2_esp32/logs/v8b2_esp32_anomaly_log.txt
```

### 6. Validação local

```
19. Abra terminal no diretório descompactado.
20. Execute:
    python scripts/validate_returned_logs.py \
        --golden logs/v8b2_esp32_golden_log.txt \
        --extended logs/v8b2_esp32_extended_log.txt \
        --anomaly logs/v8b2_esp32_anomaly_log.txt \
        --output v8b2_benchmark_summary.json

21. Verifique se parse_errors=0 e status_ok_rate=1.0.
22. Se erro, consulte TROUBLESHOOTING.md.
```

### 7. Preenchimento de templates

```
23. Preencha: return_package_template/ambiente_esp32_template.md
24. Preencha: return_package_template/resultados_execucao_template.md
25. Preencha: return_package_template/observacoes_operador_template.md
26. Mova para: retorno_v8b2_esp32/
```

### 8. Entrega

```
27. Compacte a pasta retorno_v8b2_esp32/ em ZIP.
28. Envie para o coordenador.
```

## Cronograma esperado

| Etapa | Tempo est. | Acumulado |
|-------|-----------|-----------|
| Preparação + compilação | 15 min | 15 min |
| GOLDEN | 5 min | 20 min |
| EXTENDED | 10 min | 30 min |
| ANOMALY | 3 min | 33 min |
| Validação local | 5 min | 38 min |
| Templates + retorno | 10 min | 48 min |
| **Total** | - | **~50 min** |

## Estrutura de pastas no ZIP

```
SOC_EDGE_V8B2_ESP32_HANDOFF/
├── README.md (este arquivo)
├── CHECKLIST_EXECUCAO.md
├── RESULTADOS_ESPERADOS.md
├── TEMPLATE_RETORNO_OPERADOR.md
├── MAPA_ARQUIVOS.md
├── LIMITES_DE_CLAIM.md
├── TROUBLESHOOTING.md
├── COMANDOS_VALIDACAO_LOCAL.md
├── firmware/
├── include/
├── replay/
├── anomaly/
├── validation/
├── benchmark/
├── manifests/
├── quantization_candidate/
├── scripts/
├── return_package_template/
└── [logs de referência]
```

## Comandos rápidos

Copie e cole se precisar repetir:

### Validação completa com três logs
```bash
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt \
    --json v8b2_benchmark_summary.json \
    --csv v8b2_benchmark_metrics.csv
```

### Validação apenas GOLDEN
```bash
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt
```

## Próximas etapas (não inclusas aqui)

- **V8C:** Próxima etapa de validação em stream embarcado
- **INT8 firmware:** Quantização validada em firmware (candidato offline já existe)
- **Field:** Implantação em nós reais (V8C será gateway)
- **SOH:** Trilha paralela de diagnóstico de saúde

## Contato

Se tiver dúvidas, consulte:
1. TROUBLESHOOTING.md (problemas comuns)
2. COMANDOS_VALIDACAO_LOCAL.md (exemplos de linha de comando)
3. embedded/handoff_v8b2/README.md (especificação técnica)

---

**Versão:** V8B2  
**Data:** 2026-05-19  
**Status:** Baseline lab-validado, pronto para execução operacional ESP32
