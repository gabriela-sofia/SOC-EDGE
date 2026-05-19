# Status atual do projeto — SOC/SOH embarcado em ESP32

**Atualização:** 2026-05-17

## 1. Visão geral

O projeto está atualmente estruturado em dois pipelines científicos separados:

- **SOC — State of Charge**
- **SOH — State of Health**

A separação foi mantida porque SOC e SOH têm naturezas diferentes:

- SOC estima o estado de carga em escala mais instantânea;
- SOH estima degradação/saúde da célula em escala mais lenta, por ciclo;
- os targets são diferentes;
- as features são diferentes;
- os critérios de validação também são diferentes.

Apesar disso, ambos seguem a mesma arquitetura metodológica:

```text
dataset
→ notebook científico
→ treino/validação
→ export do modelo
→ scaler/feature contract
→ firmware ESP32
→ replay offline
→ comparação Python vs ESP32
→ métricas de runtime/heap
```

---

## 2. Pipeline SOC — estado atual

O SOC foi o primeiro pipeline consolidado.

### 2.1 Objetivo inicial

O foco inicial do SOC foi:

- validar o **Method B**;
- construir um target físico consistente;
- testar learnability;
- verificar se uma MLP pequena poderia generalizar;
- avaliar se o modelo poderia ser levado para ESP32.

### 2.2 Features do SOC

O SOC usa 6 features instantâneas/temporais:

1. `voltage_v`
2. `temperature_c`
3. `current_ma`
4. `delta_voltage`
5. `delta_temperature`
6. `delta_current`

Essas features representam tensão, temperatura, corrente e variações temporais entre amostras.

### 2.3 Pipeline SOC atual

O pipeline SOC atual é:

```text
dataset
→ treino
→ export TFLite / model_data.h
→ firmware ESP32
→ replay offline
→ comparação Python vs ESP32
```

### 2.4 Validação embarcada SOC

O SOC já foi validado em replay offline embarcado, com:

- replay offline;
- `sample_id` obrigatório;
- merge auditável por `sample_id`;
- scaler consistente;
- feature order consistente;
- runtime medido;
- heap medido;
- logs reproduzíveis.

Resultados consolidados do pipeline SOC anterior:

- `120/120` amostras válidas;
- `sample_id_match = 120/120`;
- MAE Python vs ESP32 ≈ `0.0524`;
- inferência média ≈ `0.102 ms`;
- heap livre ≈ `305680 bytes`.

Essa etapa demonstrou que o modelo embarcado reproduzia o comportamento do notebook de forma consistente.

---

## 3. Validação canônica V7C/V8B2 do SOC

Depois da consolidação inicial do SOC, foi recebido o pacote canônico **V8B2**, associado ao modelo canônico **V7C**.

O objetivo dessa rodada foi mudar o claim de:

```text
O pacote canônico V7C está congelado, auditado e pronto para futura validação embarcada.
```

para:

```text
O modelo canônico V7C foi validado em replay embarcado na ESP32.
```

### 3.1 Testes executados

O pacote V8B2 exigiu três blocos de validação:

1. **GOLDEN**
   - teste principal de paridade;
   - 20 vetores canônicos;
   - validação ESP32 vs referência Python.

2. **EXTENDED**
   - replay maior;
   - 120 amostras;
   - inclui saturações esperadas;
   - avalia estabilidade e clipping correto.

3. **ANOMALY**
   - 10 cenários controlados de anomalia;
   - testa regras embarcáveis;
   - avalia recall e falso positivo.

### 3.2 Ajustes feitos no firmware

Foram necessários pequenos ajustes de compatibilidade no firmware:

- renomear arrays `B0` e `B1` para evitar conflito com macros do core Arduino/ESP32;
- substituir função de heap indisponível por `ESP.getMaxAllocHeap()`;
- ajustar a captura serial com reset controlado da ESP32.

O principal ajuste funcional ocorreu no bloco de **ANOMALY**.

O firmware original detectava apenas parte dos cenários. O protocolo V8B2 esperava 10 cenários específicos:

1. `voltage_spike`
2. `current_spike`
3. `temperature_jump`
4. `voltage_flatline`
5. `current_dropout`
6. `noise_burst`
7. `soc_temporal_incoherence`
8. `domain_shift_current_scale`
9. `low_voltage_warning`
10. `high_temperature_warning`

A função `detect_anomaly()` foi expandida para cobrir os cenários esperados pelo protocolo.

### 3.3 Resultados V8B2

Após os ajustes, os três modos passaram:

```text
GOLDEN:   PASS
EXTENDED: PASS
ANOMALY:  PASS
Overall:  PASS
```

Isso valida o modelo canônico V7C em replay embarcado na ESP32, incluindo:

- paridade canônica;
- replay estendido;
- cenários controlados de anomalia;
- métricas operacionais de latência;
- métricas de heap;
- ausência de crash/reset;
- estabilidade serial.

### 3.4 Claim atualizado

O claim atual do SOC passa a ser:

```text
O modelo canônico V7C foi validado em replay embarcado na ESP32, com paridade GOLDEN, replay EXTENDED e cenários ANOMALY controlados.
```

---

## 4. Pipeline SOH — estado atual

Depois da consolidação do SOC, a mesma infraestrutura foi reaproveitada para SOH.

O SOH é diferente do SOC porque trabalha com:

- degradação;
- comportamento por ciclo;
- estatísticas agregadas;
- histórico temporal maior;
- saúde/capacidade da célula.

### 4.1 Features do SOH

O SOH usa 16 features agregadas por ciclo:

1. `cycle_number`
2. `voltage_V_mean`
3. `voltage_V_std`
4. `voltage_V_min`
5. `voltage_V_max`
6. `temperature_C_mean`
7. `temperature_C_std`
8. `temperature_C_min`
9. `temperature_C_max`
10. `current_est_mA_mean`
11. `current_est_mA_std`
12. `current_est_mA_min`
13. `current_est_mA_max`
14. `elapsed_time_s_min`
15. `elapsed_time_s_max`
16. `cycle_duration_s`

Essas features condensam o comportamento do ciclo: tensão, temperatura, corrente, dispersão e duração.

### 4.2 Benchmark e escolha da MLP

No SOH foram usados dois tipos de modelo:

- **Random Forest**
- **MLP**

O Random Forest foi usado como benchmark tabular forte para responder se o problema era aprendível.

Resultado aproximado:

```text
Random Forest: R² ≈ 0.987
```

Esse resultado foi importante porque indicou que:

- o dataset fazia sentido;
- o target fazia sentido;
- as features carregavam sinal físico relevante;
- o problema não era aleatório.

A MLP foi usada como candidata embarcável porque:

- é exportável para TFLite;
- é mais adequada ao microcontrolador;
- tem execução mais previsível no ESP32;
- permite validação por replay embarcado.

Resultado aproximado da melhor MLP:

```text
MLP: R² ≈ 0.91
```

A MLP não foi escolhida por ser necessariamente o modelo tabular mais acurado, mas por ser o melhor compromisso entre desempenho e viabilidade embarcada.

### 4.3 Pipeline SOH atual

O pipeline SOH atual é:

```text
dataset por ciclo/célula
→ treino
→ Random Forest benchmark
→ MLP edge candidate
→ export TFLite
→ model_data.h
→ firmware ESP32
→ replay offline
→ comparação Python vs ESP32
```

### 4.4 Validação embarcada SOH

Após exportação da MLP para ESP32, o replay offline foi validado.

Resultados embarcados SOH:

- `120/120` amostras válidas;
- `sample_id_match_all = True`;
- MAE Python vs ESP32 ≈ `1e-6`;
- RMSE ≈ `1e-6`;
- inferência média ≈ `0.255 ms`;
- heap mínimo ≈ `277204 bytes`.

Isso significa que a ESP32 reproduz numericamente o comportamento do notebook para o SOH.

---

## 5. Como funciona o replay offline

A validação embarcada foi estruturada como replay offline controlado.

O notebook gera:

- features;
- scaler;
- predição Python de referência.

Depois esses dados são exportados para CSV.

Um script Python envia para a ESP32 via Serial:

```text
sample_id + features
```

A ESP32:

- recebe as features;
- aplica o scaler;
- executa o modelo;
- devolve:

```text
sample_id + inferência
```

Depois o Python:

- captura as respostas;
- faz merge por `sample_id`;
- compara notebook vs embarcado;
- calcula MAE, RMSE, runtime, heap e consistência.

Essa abordagem torna o embarcado auditável e reproduzível.

---

## 6. `sample_id` e rastreabilidade

O `sample_id` não é feature do modelo. Ele é um identificador único da amostra.

Ele garante que:

```text
a saída da ESP32 corresponde exatamente à mesma entrada enviada pelo notebook
```

Isso evita erros de merge por ordem de linha.

O fluxo fica:

```text
notebook gera sample_id
→ CSV leva sample_id + features
→ ESP32 devolve sample_id + inferência
→ Python faz merge por sample_id
→ validação compara Python vs ESP32
```

Isso permite detectar:

- perda de linha;
- resposta fora de ordem;
- reset;
- duplicação;
- parsing quebrado.

---

## 7. Estado atual do projeto

Hoje o projeto possui:

### SOC

- pipeline embarcado validado;
- replay offline validado;
- modelo canônico V7C validado no pacote V8B2;
- GOLDEN PASS;
- EXTENDED PASS;
- ANOMALY PASS.

### SOH

- dataset por ciclo/célula;
- benchmark Random Forest;
- MLP edge candidate;
- export TFLite;
- replay offline validado;
- Python vs ESP32 parity validada;
- runtime/heap medidos.

### Infraestrutura

- replay offline;
- validation packages;
- scalers auditáveis;
- feature contracts;
- logs reproduzíveis;
- runtime/heap auditados;
- firmware reproduzível.

O estado atual pode ser resumido como:

```text
pipeline TinyML reproduzível e auditável para SOC e SOH em ESP32
```

---

## 8. Próxima etapa — integração SOC + SOH

A próxima etapa é integrar SOC e SOH no mesmo runtime embarcado.

Isso não significa juntar os notebooks científicos.

A proposta é manter:

- notebook SOC separado;
- notebook SOH separado.

A razão é que:

- os targets são diferentes;
- as features são diferentes;
- os modelos são diferentes;
- as métricas científicas são diferentes.

A integração acontece no firmware/runtime embarcado.

O firmware unificado deve:

1. receber features SOC;
2. aplicar scaler SOC;
3. inferir SOC;
4. receber features SOH;
5. aplicar scaler SOH;
6. inferir SOH;
7. devolver SOC + SOH no mesmo output.

A arquitetura prevista é:

```text
features SOC
→ scaler SOC
→ modelo SOC
→ SOC_pred

features SOH
→ scaler SOH
→ modelo SOH
→ SOH_pred

output único:
sample_id,SOC,SOH,runtime_soc,runtime_soh,heap
```

Portanto, o próximo objetivo técnico é:

```text
construir um runtime unificado de inferência TinyML,
mantendo os pipelines científicos separados e auditáveis.
```
