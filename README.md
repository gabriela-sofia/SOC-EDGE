# SOC-EDGE

Este repositório organiza a versão pública do SOC Method B, voltado à estimativa leve de State of Charge (SOC) para inferência embarcada em ESP32.

O objetivo científico é manter um pipeline edge-oriented, auditável e conservador: treino offline em Python, exportação rastreável de scaler e pesos, verificação de paridade e inferência embarcada. A ESP32 executa apenas inferência; treino, seleção de modelo e validação estatística permanecem fora do firmware.

## Method B

O alvo `soc_method_b` é definido por integração acumulada de corrente:

```text
q_Ah = integral acumulada de |I| * dt / 3600
Q_cycle = throughput máximo por ciclo
soc_method_b = clip(1 - q_Ah / Q_cycle, 0, 1)
```

O modelo aprende uma aproximação leve desse alvo a partir de seis entradas canônicas:

```text
[voltage_v, temperature_c, current_ma, delta_voltage, delta_temperature, delta_current]
```

Regras de implementação:

- `current_ma` deve estar em miliampere.
- A ordem das features é fixa.
- O scaler deve reproduzir o `MinMaxScaler` usado em Python.
- Features escaladas não devem ser clipadas.
- Apenas o SOC final deve ser clipado para `[0, 1]`.

## Estado Atual do SOC

O SOC Method B é o pipeline principal do repositório. O estágio público consolidado é o V8B2. O modelo canônico V7C foi executado dentro do pacote V8B2, e o pacote V8B2 foi validado por replay embarcado na ESP32 com:

- `GOLDEN`: PASS.
- `EXTENDED`: PASS.
- `ANOMALY`: PASS.
- resultado consolidado: Overall PASS.
- latência média reportada por modo em torno de 0,2 ms ou abaixo.
- heap e serial estáveis durante os replays registrados.
- nenhum crash ou reset inesperado reportado nos testes consolidados.

Claim permitido: o pacote V8B2 foi validado por replay embarcado na ESP32.

Claims não permitidos: validação em campo, prontidão para produção, validação com sensores reais em bancada, operação 24/7 validada, validação industrial ou modelo definitivo.

## Trilha SOH

SOH é uma trilha separada de preparação metodológica. Ela não integra o pacote SOC V8B2 e não deve ser descrita como SOH operacional, diagnóstico real de degradação, predição de vida útil, manutenção preditiva, validação em campo ou produção.

## Estrutura

```text
docs/                 documentação científica, metodológica e de handoff
manifests/            registros versionáveis de datasets, experimentos e replay
src/                  código Python versionável
scripts/              scripts de preparação, validação, exportação e auditoria
embedded/             firmware, headers, replay e pacote curado V8B2
tests/                testes automatizados existentes
examples/             amostras pequenas para teste ou documentação
local_only/           orientação para materiais locais não versionáveis
```

## Dados

Dados brutos, zips, modelos binários, caches, logs e outputs massivos não fazem parte do Git. Eles são representados por documentação, manifests, schemas e checksums quando necessário. CSVs pequenos permanecem versionáveis apenas quando têm função clara de replay, anomalia, manifest ou exemplo reprodutível.

## Handoff ESP32

O handoff público curado está em `embedded/handoff_v8b2/` e a documentação correspondente está em `docs/handoff_esp32/`. Esse material registra como executar o replay, quais critérios PASS/FAIL usar, como devolver resultados e como avaliar paridade Python vs ESP32.

## Reprodução da Parte Versionável

Instale as dependências Python usadas pelo projeto e rode:

```powershell
python -m pip install -r requirements.txt
python -m pytest
```

Para validar logs retornados da ESP32 no formato V8B2, use:

```powershell
python embedded/handoff_v8b2/validation/validate_esp32_v8b2.py --help
```

Para verificar a estrutura pública do handoff V8B2:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_handoff_v8b2.ps1
```

## Features Matemáticas de Janela e Ciclo

A Fase 4B implementa camada de engenharia de features que prepara pipeline offline para otimização:

```powershell
python scripts/offline_eval/generate_window_cycle_features.py `
    --input <caminho/local.csv> `
    --output local_runs/features/output.csv `
    --window-size 5
```

Features geradas incluem deltas, slopes, carga/energia acumulada e rolling statistics. Documentação completa em `docs/otimizacao/features_janela_ciclo.md`.

## Auditoria do Pacote V8B2

O pacote V8B2 possui um manifesto canônico e um auditor estrutural:

```powershell
python scripts/check_v8b2_package.py
python scripts/run_v8b2_validation.py caminho/do/log.txt
```

O auditor verifica diretórios, arquivos obrigatórios, validador canônico, modos GOLDEN/EXTENDED/ANOMALY e limites de claim.

## Benchmark embarcado V8B2

Os logs seriais do replay V8B2 podem ser analisados sem versionar novas saídas locais:

```powershell
python scripts/parse_v8b2_benchmark.py embedded/handoff_v8b2/v8b2_esp32_golden_log.txt
python scripts/parse_v8b2_benchmark.py embedded/handoff_v8b2/v8b2_esp32_golden_log.txt embedded/handoff_v8b2/v8b2_esp32_extended_log.txt embedded/handoff_v8b2/v8b2_esp32_anomaly_log.txt --json local_runs/v8b2_benchmark_summary.json --csv local_runs/v8b2_benchmark_metrics.csv
```

Como `local_runs/` é ignorado, relatórios gerados localmente não entram no Git. O benchmark mede runtime, latência, heap e parsing do replay embarcado; ele não representa validação em campo, produção ou sensor físico real no V8B2.

## Otimização e quantização V8B2

A camada de quantização mede footprint e erro de dequantização de pesos, sem
afirmar firmware INT8 validado:

```powershell
python scripts/analyze_v8b2_model_footprint.py
python scripts/simulate_v8b2_weight_quantization.py
python scripts/compare_v8b2_float_vs_dequantized.py
python scripts/compare_v8b2_quantization_schemes.py
python scripts/export_v8b2_quantized_header.py
```

Os relatórios calculados localmente devem ficar em `local_runs/`. A MLP
`float32` do V8B2 continua sendo o baseline canônico até comparação embarcada
justa.

## Matriz de otimização científica offline

A matriz de otimização organiza frentes, métricas, splits e claims permitidos
para evoluções offline do SOC-EDGE:

```powershell
python scripts/offline_eval/check_optimization_registry.py
python scripts/offline_eval/check_evaluation_matrix.py
```

Essa camada não treina modelos novos nem altera o baseline V8B2; ela define
contratos de avaliação para as próximas fases.

## Próximo Estágio

O próximo estágio metodologicamente correto é o V8C: validação de bancada com aquisição real ou semi-real, sensor físico, descarga controlada e relatório completo de latência, RAM, flash, estabilidade e paridade. V8C ainda não é campo nem produção.
