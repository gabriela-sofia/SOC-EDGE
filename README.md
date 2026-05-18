# SOC Method B

Este repositório organiza a versão pública e versionável do projeto SOC Method B, voltado à estimativa leve de State of Charge (SOC) de baterias para execução embarcada em ESP32.

O objetivo científico é construir e validar um modelo edge-oriented, com treino offline em Python, exportação rastreável de scaler e pesos, verificação de paridade e inferência embarcada. A ESP32 executa apenas inferência; treino, seleção de modelo e validação estatística permanecem fora do firmware.

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

## Estado Atual

O estágio consolidado é o V8B2. A validação embarcada por replay na ESP32 foi concluída com:

- `GOLDEN`: PASS.
- `EXTENDED`: PASS.
- `ANOMALY`: PASS.
- resultado consolidado: Overall PASS.
- latência média reportada por modo em torno de 0,2 ms ou abaixo.
- heap e serial estáveis durante os replays registrados.
- nenhum crash ou reset inesperado reportado nos testes consolidados.

Claim permitido: o replay embarcado foi validado na ESP32 para o pacote V8B2.

Claims não permitidos: validação em campo, prontidão para produção, validação com sensores reais em bancada, ou modelo definitivo.

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
python -m pytest
```

Para validar logs retornados da ESP32 no formato V8B2, use:

```powershell
python embedded/handoff_v8b2/validation/validate_esp32_v8b2.py --help
```

## Próximo Estágio

O próximo estágio metodologicamente correto é o V8C: validação de bancada com aquisição real ou semi-real, sensor físico, descarga controlada e relatório completo de latência, RAM, flash, estabilidade e paridade.
