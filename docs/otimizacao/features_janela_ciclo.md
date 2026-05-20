# Fase 4B — Features Matemáticas de Janela e Ciclo

**Data:** 19 de maio de 2026  
**Estágio:** Implementação de camada de engenharia de features  
**Status:** COMPLETO (implementação offline, sem treino de modelo)

---

## 1. Objetivo da Fase 4B

Implementar uma **camada reprodutível de engenharia de features** matemáticas que fortaleça o pipeline offline e prepare o terreno para comparação de modelos leves (Fase 4D) e validação em bancada (V8C).

Esta fase **não treina modelo**, **não altera firmware V8B2**, e **não afirma melhoria de performance sem validação posterior**. O objetivo é criar fundação sólida, auditável e cientificamente defensável para otimização embarcada.

---

## 2. Por Que Corrente Isolada É Fraca

O modelo V8B2 baseline usa 6 features instantâneas:
- voltage_v
- temperature_c
- current_ma
- delta_voltage
- delta_temperature
- delta_current

**Limitação:** corrente instantânea isolada não captura **dinâmica temporal** da descarga. Uma célula em regime de descarga contínua tem oscilações de corrente que não revelam tendência geral de throughput.

**Solução:** agregar corrente em **contexto de ciclo inteiro** (carga acumulada) e **janela móvel** (rolling statistics).

---

## 3. Por Que Carga Acumulada Aproxima Coulomb Counting

Coulomb counting = integral de corrente ao longo do tempo:

```
Q(t) = ∫ |I(τ)| dτ
```

Se normalizarmos por capacidade de ciclo (método B):

```
SOC ≈ 1 - (Q_acumulada / Q_ciclo)
```

Isso **aproxima a lógica de Method B**. Adicionando carga acumulada como feature, o modelo tem acesso ao "histórico integrado" de consumo no ciclo, permitindo correlacionar com SOC sem replicar Method B internamente.

---

## 4. Por Que Energia Acumulada Adiciona Potência ao Throughput

Carga acumulada sozinha não leva em conta **tensão**. Duas descargas com mesma carga mas tensões diferentes têm energias diferentes:

```
E(t) = ∫ V(τ) * I(τ) dτ
```

Uma célula em **final de descarga** tem tensão mais baixa que em **início**. Energia acumulada captura esse efeito, permitindo estimar degradação ou estado de funcionamento mais preciso.

---

## 5. Por Que Slope de Tensão Captura Dinâmica de Descarga

A **taxa de mudança de tensão** durante descarga é indicadora de regime:

- **Regime inicial** (high current): slope negativo acentuado
- **Regime intermediário** (medium current): slope moderado
- **Regime final** (low current, plateau): slope muito baixo

Ao incluir `voltage_slope_v_per_s`, o modelo consegue **diferenciar regimes sem memorizar corrente isolada**, permitindo inferência mais robusta em novos ciclos.

---

## 6. Por Que Rolling Statistics Ajudam a Suavizar Ruído

Sensores reais têm ruído:

```
voltage_medida = voltage_verdadeira + ε
```

Uma **média móvel** de 5 amostras suaviza o ruído mantendo tendência:

```
rolling_voltage_mean = mean(voltage[t-4:t])
```

**Desvio padrão móvel** captura nível de ruído local; **min/max móvel** captura faixa; **skewness** captura assimetria de distribuição.

---

## 7. Features Causal vs Features Offline

### Features Causal

Usam apenas informação passada e presente (até amostra t):

```
rolling_mean_t = mean(voltage[t-window_size:t])
```

**Vantagem:** compatível com stream (pode ser computado em tempo real).  
**Exemplos:** todas as features desta Fase 4B são causais por padrão.

### Features Offline

Usam informação futura (amostra t+k):

```
rolling_mean_centered = mean(voltage[t-window_size/2:t+window_size/2])
```

**Vantagem:** mais suave, mais informativo.  
**Limitação:** requer histórico completo; não funciona em stream.  
**Status em 4B:** não implementadas (foco é stream).

---

## 8. Compatibilidade com ESP32

As features implementadas em 4B foram escolhidas por:

1. **Baixo custo computacional:** poucas operações aritméticas por amostra
2. **Memória limitada:** estatísticas móveis com buffer circular = O(window_size)
3. **Sem dependências externas:** implementadas em Python puro (sem numpy)
4. **Naturalmente causais:** podem ser adaptadas para modo stream depois

### Estimativa de Custo Embarcado

| Componente | Custo (bytes RAM) |
|---|---|
| Buffers de janela (5 amostras × 3 variáveis) | 60 |
| Acumuladores (2 scalares) | 16 |
| Features instantâneas (deltas, slopes) | 64 |
| Totals (por amostra) | ~150 bytes |

**Conclusão:** implementável em ESP32 (560 KB SRAM total).

---

## 9. List de Features Implementadas

### Grupo 1: Deltas (Primeira Ordem)

- **delta_voltage** (V): V[t] - V[t-1]
- **delta_current** (mA): I[t] - I[t-1]
- **delta_temperature** (C): T[t] - T[t-1]
- **dt_s** (s): t[t] - t[t-1] (tempo decorrido)

### Grupo 2: Slopes (Taxa de Mudança)

- **voltage_slope_v_per_s** (V/s): delta_voltage / dt_s
- **current_slope_ma_per_s** (mA/s): delta_current / dt_s
- **temperature_slope_c_per_s** (C/s): delta_temperature / dt_s

### Grupo 3: Incrementos (Janela)

- **charge_increment_ah** (Ah): integral de |I| em dt
- **energy_increment_wh** (Wh): integral de V*|I| em dt

### Grupo 4: Cumulativos (Ciclo)

- **cumulative_charge_ah** (Ah): soma de charge_increment até amostra t
- **cumulative_energy_wh** (Wh): soma de energy_increment até amostra t

**Reset:** cumuladores reiniciam quando cell_id ou cycle_id mudam.

### Grupo 5: Rolling Statistics

Para cada variável (voltage, current, temperature):

- **rolling_*_mean**: média móvel
- **rolling_*_std**: desvio padrão móvel
- **rolling_*_min**: mínimo móvel
- **rolling_*_max**: máximo móvel
- **rolling_*_skew**: assimetria (skewness) móvel

**Tamanho da janela:** configurável (padrão 5 amostras).

---

## 10. Estrutura do Código

### src/features/window_cycle_features.py

Funções puras sem dependência obrigatória de pandas:

```python
def compute_all_features(rows, window_size=5, group_keys=("cell_id", "cycle_id")):
    """Pipeline completo de engenharia de features."""
    result = rows
    result = compute_first_order_deltas(result)
    result = compute_slopes(result)
    result = compute_increment_features(result)
    result = compute_cycle_cumulative_features(result, group_keys=group_keys)
    result = compute_rolling_features(result, window_size=window_size)
    return result
```

### scripts/offline_eval/generate_window_cycle_features.py

Script CLI para gerar features a partir de CSV:

```bash
python scripts/offline_eval/generate_window_cycle_features.py \
  --input dados/local.csv \
  --output local_runs/features/output.csv \
  --window-size 5
```

**Detecção automática:**
- Coluna de tempo (timestamp_s ou elapsed_time_s)
- Colunas de grupo (cell_id, cycle_id)

**Validação:**
- Colunas obrigatórias: voltage_v, current_ma, temperature_c
- Retorna exit code 1 se validação falhar

### experiments/schemas/

- **window_cycle_feature_input_schema.csv**: schema de entrada
- **window_cycle_feature_output_schema.csv**: schema de saída

### experiments/registries/

- **feature_set_registry.csv**: registro de feature sets candidatos

| Feature Set | Objetivo | Status |
|---|---|---|
| FS_BASE_V8B2 | Features baseline V8B2 | VALIDADO |
| FS_WINDOW_001 | Deltas e slopes | CANDIDATO |
| FS_WINDOW_002 | Carga e energia acumulada | CANDIDATO |
| FS_WINDOW_003 | Rolling mean/std | CANDIDATO |
| FS_WINDOW_004 | Rolling min/max/skew | CANDIDATO |
| FS_FULL_OFFLINE_001 | Combinação completa | CANDIDATO |

---

## 11. Como Usar

### Opção 1: Importar Funções Diretamente

```python
from src.features.window_cycle_features import compute_all_features

rows = [
    {"voltage_v": 4.0, "current_ma": 100.0, "temperature_c": 25.0, "timestamp_s": 0.0, ...},
    {"voltage_v": 4.1, "current_ma": 120.0, "temperature_c": 25.1, "timestamp_s": 1.0, ...},
]

result = compute_all_features(rows, window_size=5)
# result contém todas as features originais + 30+ features novas
```

### Opção 2: Script CLI com CSV

```bash
python scripts/offline_eval/generate_window_cycle_features.py \
  --input dados/seu_dataset.csv \
  --output local_runs/features/features_janela.csv \
  --window-size 5
```

**Output:**

```
Linhas de entrada: 1000
Linhas de saída: 1000
Features geradas: 32
Grupos detectados: cell_id, cycle_id
Window size: 5
Output: local_runs/features/features_janela.csv
```

---

## 12. Testes

Suite de testes implementada em:

- **tests/features/test_window_cycle_features.py** (90+ testes)
- **tests/offline_eval/test_generate_window_cycle_features.py** (integração com CSV)

**Cobertura:**

- Funções matemáticas básicas (conversão, diff, dt)
- Carga e energia (incremento, acumulativo)
- Slopes (com proteção contra dt=0)
- Rolling stats (mean, std, min, max, skew)
- Pipeline completo (deltas → slopes → rolling)
- Reset de acumuladores ao mudar grupo
- Validação de CSV (colunas obrigatórias, detecção automática)

**Executar:**

```bash
python -m pytest tests/features/ -v
python -m pytest tests/offline_eval/test_generate_window_cycle_features.py -v
```

---

## 13. Limites Explícitos

### ❌ Não Faz Esta Fase

- ❌ **Não treina modelo:** features são apenas preparadas, não otimizadas
- ❌ **Não altera V8B2:** modelo canônico permanece congelado
- ❌ **Não afirma melhoria:** sem benchmark de modelo ainda
- ❌ **Não valida campo:** tudo é offline até V8C
- ❌ **Não muda firmware:** puro Python/CSV

### ✅ O Que Faz

- ✅ Implementa funções matemáticas puras e testáveis
- ✅ Cria schema de entrada/saída públicos
- ✅ Registra feature sets candidatos
- ✅ Fornece script CLI para geração
- ✅ Prepara Fase 4D (comparação de modelos)

---

## 14. Próximos Passos

### Fase 4C: Splits Robustos

- Leave-one-cell-out (LOCO) por célula
- Leave-one-cycle-out (LOCO) por ciclo
- Splits temporais (treino histórico, teste futuro)
- Validação cross-domain

### Fase 4D: Comparação de Modelos Leves

- MLP menor (500 parâmetros)
- 1D-CNN leve
- Ridge baseline
- Comparação com FS_BASE_V8B2 como baseline

### Fase 4E: Fixed-Point Reference

- Conversão de pesos para ponto fixo
- Validação de truncamento

### Fase 4F: Anomalias v2

- Regras físicas (jumps, coerência)
- Severidade e persistência

### Fase 4G: Runtime Replay/Stream

- Modo replay vs modo stream
- Preparação para V8C

### Fase 4H: SOH Extension

- Capacidade efetiva por ciclo
- Degradação como extensão
- Sem claim operacional

---

## 15. Referências

- **Carga acumulada:** similar a Coulomb counting simplificado
- **Energia acumulada:** W = V × I (integração numérica)
- **Slopes:** primeira derivada discreta
- **Rolling statistics:** janela causal (não usa informação futura)
- **Skewness:** assimetria de terceiro momento normalizado

---

## 16. Conclusão

A Fase 4B estabelece a camada de **engenharia de features matemáticas** de janela/ciclo, necessária para ponte entre baseline V8B2 (features instantâneas) e modelos otimizados (Fase 4D). As features são causais, interpretáveis e compatíveis com ESP32, preparando terreno para validação offline (4D), bancada (V8C) e campo futuro.
