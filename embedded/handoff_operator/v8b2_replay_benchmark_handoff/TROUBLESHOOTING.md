# Troubleshooting — V8B2 ESP32 Handoff

Se encontrar problemas durante execução, este guia pode ajudar.

---

## Problemas de Compilação

### Problema: Arquivo não encontrado (firmware_soc_v8b2_canonical.ino)

**Sintoma:**
```
fatal error: firmware_soc_v8b2_canonical.ino: No such file or directory
```

**Causa provável:**
- Arquivo não está em `firmware/` ou caminho incorreto.
- IDE não está na raiz do ZIP.

**Ação:**
1. Confirme que está em: `SOC_EDGE_V8B2_ESP32_HANDOFF/firmware/firmware_soc_v8b2_canonical.ino`
2. Em Arduino IDE: abra manualmente `File → Open → firmware_soc_v8b2_canonical.ino`
3. Se ainda não funcionar, descompacte novamente o ZIP.

---

### Problema: Header files não encontrados

**Sintoma:**
```
fatal error: canonical_model_weights_v8b2.h: No such file or directory
```

**Causa provável:**
- Pasta `include/` não está no mesmo diretório do `.ino`.
- IDE não sabe onde procurar headers.

**Ação:**
1. Certifique-se de que `firmware/` e `include/` estão lado a lado:
   ```
   SOC_EDGE_V8B2_ESP32_HANDOFF/
   ├── firmware/
   │   └── firmware_soc_v8b2_canonical.ino
   ├── include/
   │   ├── canonical_model_weights_v8b2.h
   │   └── replay_vectors_v8b2.h
   ```

2. Em Arduino IDE:
   - `Sketch → Show Sketch Folder`
   - Confirme que `include/` está acessível ou copie headers para sketch folder.

3. Em PlatformIO:
   - Edite `platformio.ini` para adicionar:
     ```
     build_flags = -I../include
     ```

---

### Problema: Erro de compilação "unknown type name" ou macro not found

**Sintoma:**
```
error: unknown type name 'MLP_INPUT_SIZE'
```

**Causa provável:**
- Define ou tipo não está sendo incluído.
- Header foi corrompido na descompactação.

**Ação:**
1. Verifique que `canonical_model_weights_v8b2.h` começa com:
   ```cpp
   #ifndef CANONICAL_MODEL_WEIGHTS_V8B2_H
   #define CANONICAL_MODEL_WEIGHTS_V8B2_H
   #define MLP_INPUT_SIZE 6
   ```

2. Se corrompido, extraia novamente do ZIP.

3. Se problema persistir, verifique encoding (UTF-8, não UTF-16).

---

### Problema: "Board not found" ou "Port not available"

**Sintoma:**
```
Error: Board not found in selected platform
```

**Causa provável:**
- Core ESP32 não instalado.
- Placa não reconhecida.

**Ação em Arduino IDE:**
1. `Tools → Board → Boards Manager`
2. Procure por: `esp32`
3. Instale: `esp32 by Espressif Systems` (versão 2.0.8 ou 3.0.0)
4. Feche e reabra Arduino.
5. `Tools → Board → ESP32 → ESP32 Dev Module` ou seu modelo exato.

**Ação em PlatformIO:**
1. Certifique-se de que `platformio.ini` contém:
   ```
   [env:esp32dev]
   platform = espressif32
   board = esp32doit-devkit-v1
   framework = arduino
   ```

2. Terminal: `pio run -t build`

---

## Problemas de Upload

### Problema: "Failed to open COM port" ou "Port busy"

**Sintoma:**
```
error: Failed to open COM port 'COM3'
serial.serialutil.SerialException: Port is already open
```

**Causa provável:**
- Serial Monitor ainda está aberto.
- Outro programa está usando a porta.
- Cabo USB desligou ou não está bem encaixado.

**Ação:**
1. Feche Serial Monitor (Arduino IDE).
2. Feche qualquer outra ferramenta que use serial (Putty, minicom).
3. Desconecte e reconecte o cabo USB.
4. Verifique se porta aparece em `Device Manager` (Windows):
   - `Device Manager → Ports (COM & LPT)`
   - Deve aparecer como `USB-to-UART` ou `CH340`.
   - Se aparecer com "?" ou warning, driver está faltando.

5. Se driver faltando, download de: `https://github.com/espressif/esptool` (instruções incluem drivers).

---

### Problema: "A timeout occurred" ou "Failed to connect to port"

**Sintoma:**
```
A timeout occurred trying to connect to the development board
```

**Causa provável:**
- Cabo USB fraco ou com mau contato.
- Baud rate errado.
- Bootloader não respondendo.

**Ação:**
1. Tente outro cabo USB (use USB 2.0 confiável).
2. Desconecte, aguarde 3 segundos, reconecte.
3. Coloque a placa em modo bootloader:
   - Segure **BOOT** + **EN** simultaneamente.
   - Solte **EN** primeiro, depois **BOOT**.
   - Tente upload novamente.

---

## Problemas de Serial / Logs

### Problema: Serial Monitor não mostra mensagens

**Sintoma:**
```
Serial Monitor abre, mas sem nenhuma mensagem.
```

**Causa provável:**
- Baud rate incorreto.
- Firmware não iniciou ou travou.
- Monitor conectado após firmware já estar rodando.

**Ação:**
1. Verifique baud rate:
   - Código deve estar setado para: `Serial.begin(115200);`
   - Serial Monitor deve estar em: **115200 baud** (canto inferior direito).

2. Resetar placa:
   - Pressione botão **EN** na ESP32.
   - Observe se aparece qualquer mensagem (boot, inicialização).

3. Se firmware estava rodando antes de abrir monitor:
   - Reset e observe desde o início.

---

### Problema: Serial Monitor mostra caracteres garbled / ilegíveis

**Sintoma:**
```
ä¥ü°ÿô≤â±£¤¨©ª«¬ªùü∞∫˜
```

**Causa provável:**
- Baud rate não corresponde (ex: 115200 esperado, 9600 configurado).
- Cabo USB com interferência.

**Ação:**
1. Confirme baud rate no código:
   ```cpp
   Serial.begin(115200);  // V8B2 usa 115200
   ```

2. Confirme baud rate no Serial Monitor: **115200**

3. Se problema persistir, tente baud rates alternativos:
   - 9600, 57600, 230400 (não esperado, mas teste).

4. Se ainda garbled, problema pode ser cabo; tente outro cabo USB.

---

### Problema: Comandos digitados (GOLDEN, EXTENDED, ANOMALY) não são reconhecidos

**Sintoma:**
```
Você digita: GOLDEN
Nada acontece; nenhuma resposta.
```

**Causa provável:**
- Entrada serial não está sendo lida.
- Modo de replay não está ativo.
- Firmware esperando entrada diferente.

**Ação:**
1. Verifique que após upload, placa imprime mensagem de inicialização.
2. Tente digitar: `GOLDEN` + **ENTER**
3. Certifique-se de que "Newline" está selecionado em Serial Monitor (canto inferior direito).
4. Se ainda não funciona, verifique firmware em `firmware/firmware_soc_v8b2_canonical.ino`:
   - Deve ter função `handleSerialInput()` ou similar que lê GOLDEN/EXTENDED/ANOMALY.
5. Consulte `embedded/handoff_v8b2/README.md` para protocolo serial específico.

---

### Problema: Log tem linhas corrompidas ou campos ausentes

**Sintoma:**
```
sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap...
1,GOLDEN,0.855,0.164,35è1068,351068,12288,0,0,OK
                      ↑ caractere estranho
```

**Causa provável:**
- Cabo USB com ruído.
- Baud rate instável.
- Buffer serial overflow.

**Ação:**
1. Tente cabo diferente (USB 2.0).
2. Confirme baud rate: 115200.
3. Se problema persistir, tente reduzir frequência ESP32:
   - `Tools → CPU Frequency → 80 MHz` (ao invés de 240 MHz).
4. Repetir replay e verificar se linhas melhoram.

Se não melhorar:
- Salve o log mesmo assim.
- Anote no template: "Houve X linhas corrompidas; investigar estabilidade serial."

---

## Problemas de Execução do Replay

### Problema: Replay começa mas não termina

**Sintoma:**
```
[GOLDEN_START]
1,GOLDEN,0.855,...
2,GOLDEN,0.856,...
[... após 1 minuto, nada mais]
```

**Causa provável:**
- Loop infinito ou deadlock.
- Placa travou silenciosamente.
- Buffer serial muito lento.

**Ação:**
1. Aguarde 2-3 minutos; às vezes é apenas lento.
2. Se nada acontecer, pressione **EN** para resetar.
3. Se resetar abre loop, problema é no firmware; contacte suporte.

---

### Problema: Muitos resets durante execução

**Sintoma:**
```
[... log começa]
[Placa reseta, mostra boot message]
[Log começa novamente]
```

**Causa provável:**
- Stack overflow ou memory corruption.
- Watchdog timer ativado (timeout em loop longo).
- Power instável (cabo USB fraco).

**Ação:**
1. Tente com cabo USB diferente e power supply separado (se disponível).
2. Aumente stack size se possível (PlatformIO):
   ```
   build_flags = -DCONFIG_ARDUINO_LOOP_STACK_SIZE=8192
   ```

3. Se resets continuarem, problema pode ser no firmware; anote nos templates e reporte.

---

### Problema: Heap muito baixo (<50 KB)

**Sintoma:**
```
free_heap: 45000
min_free_heap: 32000
```

**Causa provável:**
- Vazamento de memória.
- Buffer muito grande.
- Stack crescendo indevidamente.

**Ação:**
1. Isto é preocupante. Anote nos templates.
2. Se resets também ocorrem, aumentar prioridade de investigação.
3. Tente com firmware v8b2 sem modificações locais.
4. Se persistir, reporte como crítico.

---

## Problemas de Validação Local

### Problema: Script Python não encontra logs

**Sintoma:**
```
FileNotFoundError: No such file or directory: 'logs/v8b2_esp32_golden_log.txt'
```

**Causa provável:**
- Path incorreto ou arquivo não existe.
- Rodando script de diretório errado.

**Ação:**
1. Confirme que está no diretório raiz do ZIP:
   ```
   C:\...\SOC_EDGE_V8B2_ESP32_HANDOFF>
   ```

2. Confirme que logs existem:
   ```
   ls logs/v8b2_esp32_*.txt
   ```

3. Se não existem, salve-os:
   ```
   logs/v8b2_esp32_golden_log.txt
   logs/v8b2_esp32_extended_log.txt
   logs/v8b2_esp32_anomaly_log.txt
   ```

---

### Problema: "parse_errors > 0" ao validar

**Sintoma:**
```
V8B2 validation
Total records: 150
Parse errors: 5
Status: FAIL
```

**Causa provável:**
- Linhas corrompidas no log.
- Schema esperado não corresponde.

**Ação:**
1. Verifique estrutura do log; deve ter 10 campos:
   ```
   sample_id,mode,soc_final,inference_time_ms,free_heap,min_free_heap,max_alloc_heap,anomaly_flag,anomaly_code,status
   ```

2. Se campos faltam ou estão fora de ordem, protocolo mudou.

3. Tente regenerar log com replay novo.

4. Se erro persistir, reporte em templates com detalhe de linhas problemáticas.

---

### Problema: "status_ok_rate < 1.0"

**Sintoma:**
```
Status OK rate: 0.95
Status fail count: 5
```

**Causa provável:**
- Alguma amostra retornou status=FAIL ao invés de OK.
- Pode indicar problema no modelo ou detecção.

**Ação:**
1. Examine log manualmente para ver quais linhas têm status != OK:
   ```
   grep -v ",OK$" logs/v8b2_esp32_*.txt
   ```

2. Anote em templates qual modo e qual amostra falhou.

3. Isto é raro e pode indicar problema; reporte detalhadamente.

---

### Problema: Script não consegue importar bibliotecas Python

**Sintoma:**
```
ModuleNotFoundError: No module named 'csv'
```

**Causa provável:**
- Python não está instalado corretamente.
- Versão Python muito antiga (< 3.8).

**Ação:**
1. Confirme Python 3.10+:
   ```
   python --version
   ```

2. Se < 3.10, upgrade: `https://python.org`

3. Roda novamente:
   ```
   python scripts/validate_returned_logs.py --golden logs/v8b2_esp32_golden_log.txt
   ```

---

### Problema: PowerShell script não executa

**Sintoma:**
```
PowerShell: File cannot be loaded because running scripts is disabled
```

**Causa provável:**
- Execution Policy bloqueado no Windows.

**Ação:**
1. Abra PowerShell como Admin.
2. Execute:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. Confirme: `Y`

4. Tente novamente.

Alternativamente, execute Python diretamente:
```bash
python scripts/validate_returned_logs.py --golden logs/v8b2_esp32_golden_log.txt
```

---

## Checklist de Diagnóstico Rápido

Se algo falhar, rode este diagnóstico:

```bash
# 1. Confirme que você está na raiz do ZIP
ls README.md CHECKLIST_EXECUCAO.md

# 2. Confirme que firmware existe
ls firmware/firmware_soc_v8b2_canonical.ino

# 3. Confirme que headers existem
ls include/canonical_model_weights_v8b2.h
ls include/replay_vectors_v8b2.h

# 4. Confirme que scripts existem
ls scripts/validate_returned_logs.py

# 5. Confirme que logs foram salvos
ls logs/v8b2_esp32_golden_log.txt
ls logs/v8b2_esp32_extended_log.txt
ls logs/v8b2_esp32_anomaly_log.txt

# 6. Se tudo existe, tente validação
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt
```

Se algum passo falhar, anote o número e o erro, e consulte a seção correspondente acima.

---

## Se Ainda Estiver Travado

1. **Documente tudo:**
   - Qual foi o passo que falhou?
   - Qual foi a mensagem exata de erro?
   - Qual é seu hardware (IDE, versão, placa)?

2. **Preench templates mesmo assim:**
   - Anote o erro em `observacoes_operador_template.md`.
   - Envie o que conseguir fazer.

3. **Dica final:**
   - Resetar placa (botão EN).
   - Desligar e religar USB.
   - Extrair ZIP novamente se arquivo corrompido.

---

**Versão:** V8B2 · 2026-05-19

**Última resort:** Se nada funcionar, reporte o erro com máximo detalhe nos templates de retorno e envie mesmo assim para diagnóstico.
