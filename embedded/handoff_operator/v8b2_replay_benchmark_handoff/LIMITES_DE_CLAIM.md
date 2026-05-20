# Limites de Claims — V8B2 Handoff Operacional

Este documento define explicitamente **o que você PODE e NÃO PODE afirmar** ao reportar seus resultados.

---

## Tabela de Claims Permitidos e Proibidos

| Tema | ✅ PERMITIDO | ❌ PROIBIDO |
|------|-----------|-----------|
| **Validação** | Replay embarcado V8B2 confirmado em ESP32 | V8B2 validado em campo |
| | Paridade de inferência (log vs esperado) | Operação 24/7 contínua |
| | Benchmark embarcado (latência, heap) | Produção ready |
| **Sensor** | Stream digital / replay (dados injetados) | Sensor físico real validado |
| | Dados reproduzidos de laboratório | Medição de bateria real no V8B2 |
| **Modelo** | MLP V8B2 (6 entrada, 64-32-1 arquitetura) | Versão V8C (próxima etapa) |
| | Footprint estimado float32 (~10 KB) | INT8 firmware embarcado |
| | INT8 candidato offline comparado | INT8 validado embarcado |
| **Anomalias** | Detecção em cenários controlados (injetados) | Detecção de falha real de bateria |
| | Flags esperadas no replay ANOMALY | Diagnóstico operacional de degradação |
| | Thresholds testados em laboratório | Field anomaly detection working |
| **SOH** | Trilha separada, não inclusa | SOH operacional / predição de vida útil |
| | Baseline Ridge em Oxford/LG como referência | SOH embarcado em ESP32 |
| **Performance** | Latência mean 0.14 ms em EXTENDED | Latência garantida < 0.1 ms |
| | Heap min 351 KB em execução | Sem vazamento de memória confirmado |
| | Resets zero em 3 replays | Estabilidade 24/7 |
| **Hardware** | Validado em ESP32 DevKit V1 e equivalentes | Outras placas não testadas |
| | Flash 4 MB suficiente | Otimizado para qualquer hardware |

---

## Claims Específicos por Componente

### ✅ V8B2 (Method B Coulombic SOC)

**O que você PODE dizer:**

- "V8B2 MLP foi executado com sucesso no ESP32 via replay embarcado."
- "Modelo MLP obteve paridade com referência laboratório (RMSE < 0.02)."
- "Latência de inferência média: 0.135 ms em EXTENDED."
- "Heap utilizado: mínimo 351 KB; sem overflow detectado."
- "Anomalias foram detectadas 100% nas amostras injetadas do cenário ANOMALY."
- "Nenhum reset ou crash observado durante 3 replays completos."

**O que NÃO pode dizer:**

- ~~"V8B2 está pronto para produção."~~
- ~~"V8B2 foi validado em campo."~~
- ~~"V8B2 pode ser usado em baterias reais sem testes adicionais."~~
- ~~"V8B2 garante predição de vida útil com 95% confiança."~~

---

### ✅ Replay Embarcado

**O que você PODE dizer:**

- "Replay GOLDEN (20 amostras) completou com sucesso; 0 erros de parse."
- "Replay EXTENDED (120 amostras) foi estável; heap variação < 5%."
- "Replay ANOMALY (10 amostras injetadas) detectou 100% das anomalias esperadas."

**O que NÃO pode dizer:**

- ~~"O sistema está pronto para operação de campo."~~
- ~~"Dados brutos vêm de sensor físico real."~~
- ~~"Operação 24/7 foi testada."~~

---

### ✅ Latência e Performance

**O que você PODE dizer:**

- "Latência média de inferência: 0.143 ms (GOLDEN), 0.135 ms (EXTENDED), 0.207 ms (ANOMALY)."
- "Latência p95: [seu valor] ms."
- "Tempo total para 3 replays (150 amostras): ~20 segundos."
- "Heap mínimo observado: [seu valor] bytes."
- "Nenhuma fragmentação crítica ou vazamento observado."

**O que NÃO pode dizer:**

- ~~"Latência garantida < 0.1 ms em todas as circunstâncias."~~
- ~~"Performance é 10% melhor que [outro modelo] sem testes comparativos."~~
- ~~"Sem nenhuma overhead de software."~~

---

### ✅ Anomalias

**O que você PODE dizer:**

- "Anomalias em ANOMALY foram detectadas conforme protocolo; 10/10 amostras marcadas."
- "Tipos de anomalia testados: [listar do manifest anomaly_manifest_v8b2.csv]."
- "Nenhum falso positivo em GOLDEN/EXTENDED (anomaly_rate=0)."
- "Thresholds operacionais validados em laboratório."

**O que NÃO pode dizer:**

- ~~"Sistema pode detectar qualquer anomalia de bateria em campo."~~
- ~~"False negative rate < 1% (sem dados de teste em falhas reais)."~~
- ~~"Diagnóstico de degradação operacional."~~
- ~~"Predição de falha com X% confiança."~~

---

### ❌ Tópicos Completamente Fora de Escopo

**Não mencione no seu relatório:**

1. **Campo / Produção**
   - Nenhuma validação de campo foi feita.
   - Isto é laboratório com dados sintetizados.

2. **Sensor Físico Real**
   - Não há bateria real na placa.
   - Todos os dados são de stream digital/replay.

3. **V8C ou Versões Futuras**
   - V8C é próxima etapa; não inclusa aqui.
   - Não faça extrapolações sobre V8C baseadas em V8B2.

4. **INT8 Firmware Embarcado**
   - INT8 é apenas candidato offline.
   - Não foi compilado/testado em firmware real.

5. **SOH / Saúde da Bateria**
   - SOH é trilha paralela separada.
   - Não faz parte do V8B2.

6. **Vida Útil / Degradação Operacional**
   - Não há dados para fazer estas previsões.
   - Phase 3C (field) poderia contribuir, mas ainda não disponível.

---

## Como Estruturar Seu Relatório

### ✅ Estrutura Recomendada

```
## Execução V8B2 — ESP32 Replay Benchmark

### Objetivo
Confirmar operacional que o pipeline V8B2 funciona embarcado no ESP32
com paridade aos resultados de laboratório.

### Resultados
- **GOLDEN:** 20 amostras, latência média 0.164 ms, heap min 351 KB, status OK 100%
- **EXTENDED:** 120 amostras, latência média 0.135 ms, heap min 351 KB, status OK 100%
- **ANOMALY:** 10 amostras injetadas, anomalias detectadas 10/10, status OK 100%

### Estabilidade
- Resets observados: 0
- Erros de parse: 0
- Linhas corrompidas: 0

### Conclusão
V8B2 replay foi executado com sucesso em ESP32 DevKit V1, confirmando
a operacionalidade do firmware canônico e paridade de inferência com
referência laboratório.

### Limitações
- Este é teste embarcado; não validação de campo.
- Dados são stream digital/replay; sem sensor físico real.
- Não valida operação 24/7 ou cenários de produção.
```

### ❌ Evite

```
❌ "V8B2 está ready para produção."
❌ "Sistema detecta qualquer falha de bateria."
❌ "Vida útil pode ser predita com 95% confiança."
❌ "Operação 24/7 validada."
❌ "INT8 firmware está pronto."
```

---

## Resumo de Uma Linha

> **"V8B2 MLP replay foi executado com sucesso no ESP32, confirmando paridade de inferência e estabilidade em cenários embarcados controlados."**

---

## Em Caso de Dúvida

- Consulte RESULTADOS_ESPERADOS.md para valores aceitáveis.
- Consulte MAPA_ARQUIVOS.md para entender cada componente.
- Consulte TROUBLESHOOTING.md se algo sair fora do esperado.
- Mantenha observações factuais; não especule sobre aplicações futuras.

---

**Versão:** V8B2 · 2026-05-19

**Lembre-se:** Integridade científica > claims otimistas. Documente o que foi testado, não o que se espera da produção.
