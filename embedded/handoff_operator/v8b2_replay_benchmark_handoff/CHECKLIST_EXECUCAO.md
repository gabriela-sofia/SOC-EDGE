# Checklist de Execução V8B2

Use este checklist para acompanhar o progresso. Marque conforme avança:

## Preparação

- [ ] Placa ESP32 identificada (DevKit V1 ou modelo equivalente)
- [ ] Ambiente anotado (Arduino IDE / PlatformIO / ESP-IDF)
- [ ] Versão do core Arduino/ESP32 informada
- [ ] Cabo USB testado e confirmado como funcional
- [ ] Porta serial identificada e acessível

## Compilação

- [ ] Firmware V8B2 canônico localizado em `firmware/firmware_soc_v8b2_canonical.ino`
- [ ] Arquivo de headers `include/canonical_model_weights_v8b2.h` presente
- [ ] Arquivo de vetores `include/replay_vectors_v8b2.h` presente
- [ ] Firmware compilado SEM ERRO
- [ ] Flash usado registrado (aparece ao final da compilação)
- [ ] Firmware feito upload com sucesso
- [ ] Serial Monitor confirmado operacional (baud rate correto)

## Execução GOLDEN

- [ ] Comando GOLDEN digitado e enviado
- [ ] Log serial começou com `[GOLDEN_START]`
- [ ] Linhas com modo=GOLDEN recebidas
- [ ] Log serial terminou com `[GOLDEN_END]`
- [ ] Ausência de linhas corrompidas / garbled
- [ ] Ausência de resets inesperados durante GOLDEN
- [ ] Log GOLDEN salvo em `retorno_v8b2_esp32/logs/v8b2_esp32_golden_log.txt`
- [ ] Total de records GOLDEN confirmado (esperado: ~20)

## Execução EXTENDED

- [ ] Comando EXTENDED digitado e enviado (após GOLDEN terminar)
- [ ] Log serial começou com `[EXTENDED_START]`
- [ ] Linhas com modo=EXTENDED recebidas
- [ ] Log serial terminou com `[EXTENDED_END]`
- [ ] Ausência de linhas corrompidas
- [ ] Ausência de resets inesperados durante EXTENDED
- [ ] Log EXTENDED salvo em `retorno_v8b2_esp32/logs/v8b2_esp32_extended_log.txt`
- [ ] Total de records EXTENDED confirmado (esperado: ~120)

## Execução ANOMALY

- [ ] Comando ANOMALY digitado e enviado (após EXTENDED terminar)
- [ ] Log serial começou com `[ANOMALY_START]`
- [ ] Linhas com modo=ANOMALY recebidas
- [ ] Log serial terminou com `[ANOMALY_END]`
- [ ] Ausência de linhas corrompidas
- [ ] Ausência de resets inesperados durante ANOMALY
- [ ] Log ANOMALY salvo em `retorno_v8b2_esp32/logs/v8b2_esp32_anomaly_log.txt`
- [ ] Total de records ANOMALY confirmado (esperado: ~10)

## Análise de Métricas

- [ ] Latência média (esperado: 0.1–0.2 ms, OK até 1 ms)
- [ ] Latência p95 registrada
- [ ] Latência p99 registrada (se capturada)
- [ ] Latência máxima registrada
- [ ] Heap mínimo durante execução registrado (esperado: > 100 KB)
- [ ] Resets / crashes durante execução: **NENHUM esperado**
- [ ] Anomaly rate em ANOMALY (esperado: 1.0, i.e., todas as amostras marcadas)

## Validação Local

- [ ] Python 3.10+ disponível
- [ ] Dependências instaladas (scripts/requirements.txt se houver)
- [ ] Script `scripts/validate_returned_logs.py` executado com três logs
- [ ] Resultado: `parse_errors=0` ✓
- [ ] Resultado: `status_ok_rate=1.0` ✓
- [ ] JSON de summary gerado (ou impresso)
- [ ] CSV de metrics gerado (ou impresso)
- [ ] Nenhum aviso crítico retornado

## Preenchimento de Templates

- [ ] `ambiente_esp32_template.md` preenchido com dados reais
  - [ ] Placa / chip / frequência
  - [ ] IDE / versão do core
  - [ ] Bibliotecas relevantes
  - [ ] Alterações locais (se houver)
  - [ ] Flash usado compilação
- [ ] `resultados_execucao_template.md` preenchido
  - [ ] Totais e erros de parse
  - [ ] Latência (mean, p95, p99, max)
  - [ ] Heap (min, max_alloc se disponível)
  - [ ] Resets/crashes confirmados como ausentes
  - [ ] Status final: PASS/FAIL
- [ ] `observacoes_operador_template.md` preenchido com qualquer observação relevante

## Compactação e Entrega

- [ ] Pasta `retorno_v8b2_esp32/` contém:
  - [ ] `ambiente_esp32.md`
  - [ ] `resultados_execucao.md`
  - [ ] `observacoes_operador.md`
  - [ ] `v8b2_benchmark_summary.json` (se gerado)
  - [ ] `v8b2_benchmark_metrics.csv` (se gerado)
  - [ ] `logs/v8b2_esp32_golden_log.txt`
  - [ ] `logs/v8b2_esp32_extended_log.txt`
  - [ ] `logs/v8b2_esp32_anomaly_log.txt`
- [ ] Folder compactada em ZIP
- [ ] ZIP renomeado com data: `retorno_v8b2_esp32_YYYYMMDD.zip`
- [ ] ZIP pronto para envio

## Resumo Final

- **Data de execução:** ________
- **Operador:** ________
- **Placa:** ________
- **Resultado:** ☐ PASS (todos os checks) ☐ FAIL (revisar dúvidas acima)
- **Observações:** ________

---

**Dica:** Se algum check falhar, consulte TROUBLESHOOTING.md antes de tentar novamente.
