# Instruções de Devolução — Pacote V8B2 ESP32

## Estrutura de Retorno Esperada

Você deve devolver uma pasta com este nome e estrutura:

```
retorno_v8b2_esp32/
├── ambiente_esp32.md                  [preenchido por você]
├── resultados_execucao.md             [preenchido por você]
├── observacoes_operador.md            [preenchido por você]
├── v8b2_benchmark_summary.json        [gerado automaticamente pelo script]
├── v8b2_benchmark_metrics.csv         [gerado automaticamente pelo script]
└── logs/
    ├── v8b2_esp32_golden_log.txt      [log bruto do Serial Monitor]
    ├── v8b2_esp32_extended_log.txt    [log bruto do Serial Monitor]
    └── v8b2_esp32_anomaly_log.txt     [log bruto do Serial Monitor]
```

---

## Passo a Passo

### 1. Preparar Pasta de Retorno

Crie uma pasta chamada `retorno_v8b2_esp32`:

```bash
mkdir retorno_v8b2_esp32
mkdir retorno_v8b2_esp32/logs
```

### 2. Salvar Logs Brutos

Durante a execução de cada replay (GOLDEN, EXTENDED, ANOMALY):

1. Abra Serial Monitor
2. Selecione baud rate **115200**
3. Digite comando (ex: `GOLDEN` + ENTER)
4. Aguarde até ver `[GOLDEN_END]`
5. **Copie tudo** (cmd+A, cmd+C ou ctrl+A, ctrl+C)
6. Salve em arquivo de texto:
   - `retorno_v8b2_esp32/logs/v8b2_esp32_golden_log.txt`
   - `retorno_v8b2_esp32/logs/v8b2_esp32_extended_log.txt`
   - `retorno_v8b2_esp32/logs/v8b2_esp32_anomaly_log.txt`

**Dica:** Em Arduino IDE, é possível também salvar pelo menu: Serial Monitor → ícone de salvar.

### 3. Executar Validação Local

Do diretório raiz do handoff:

```bash
python scripts/validate_returned_logs.py \
    --golden logs/v8b2_esp32_golden_log.txt \
    --extended logs/v8b2_esp32_extended_log.txt \
    --anomaly logs/v8b2_esp32_anomaly_log.txt \
    --json retorno_v8b2_esp32/v8b2_benchmark_summary.json \
    --csv retorno_v8b2_esp32/v8b2_benchmark_metrics.csv
```

Isto gera:
- `v8b2_benchmark_summary.json` — resumo em JSON
- `v8b2_benchmark_metrics.csv` — métricas em CSV

Copie/mova estes arquivos para `retorno_v8b2_esp32/`.

### 4. Preencher Templates

Você encontra os templates em: `return_package_template/`

Copie para sua pasta de retorno:

```bash
cp return_package_template/ambiente_esp32_template.md retorno_v8b2_esp32/ambiente_esp32.md
cp return_package_template/resultados_execucao_template.md retorno_v8b2_esp32/resultados_execucao.md
cp return_package_template/observacoes_operador_template.md retorno_v8b2_esp32/observacoes_operador.md
```

Abra cada arquivo e **preencha com seus dados reais:**

- **ambiente_esp32.md:** Hardware, IDE, versão do core, bibliotecas, Flash usado
- **resultados_execucao.md:** Latência, heap, resets, anomalias detectadas, status
- **observacoes_operador.md:** Qualquer observação relevante (problemas, estabilidade, etc.)

### 5. Verificar Estrutura Final

Confirme que sua pasta contém tudo:

```bash
ls -R retorno_v8b2_esp32/
```

Esperado:
```
retorno_v8b2_esp32/:
ambiente_esp32.md
resultados_execucao.md
observacoes_operador.md
v8b2_benchmark_summary.json
v8b2_benchmark_metrics.csv
logs/

retorno_v8b2_esp32/logs/:
v8b2_esp32_golden_log.txt
v8b2_esp32_extended_log.txt
v8b2_esp32_anomaly_log.txt
```

### 6. Compactar em ZIP

```bash
# Windows (PowerShell)
Compress-Archive -Path retorno_v8b2_esp32 -DestinationPath retorno_v8b2_esp32.zip

# ou (cmd)
tar -a -c -f retorno_v8b2_esp32.zip retorno_v8b2_esp32

# macOS/Linux
zip -r retorno_v8b2_esp32.zip retorno_v8b2_esp32
```

### 7. Enviar

Envie o ZIP gerado (`retorno_v8b2_esp32.zip`) para o coordenador.

---

## Checklist de Devolução

- [ ] Pasta `retorno_v8b2_esp32/` criada
- [ ] 3 logs salvos em `logs/`
- [ ] Script `validate_returned_logs.py` executado com sucesso
- [ ] JSON e CSV salvos na pasta de retorno
- [ ] `ambiente_esp32.md` preenchido e salvo
- [ ] `resultados_execucao.md` preenchido e salvo
- [ ] `observacoes_operador.md` preenchido e salvo
- [ ] Pasta compactada em ZIP
- [ ] ZIP não tem mais de 10 MB (esperado: 1-3 MB)
- [ ] Pronto para envio

---

## Tamanho Esperado

Seu ZIP deverá ser pequeno:

| Componente | Tamanho est. |
|-----------|-------------|
| 3 logs (~150 registros) | 30-50 KB |
| JSON + CSV | 5-10 KB |
| Templates preenchidos | 10-20 KB |
| **Total ZIP** | **~50-80 KB** |

Se ZIP > 5 MB, pode ter incluído algo inesperado (binários, outputs, etc.). Revise conteúdo.

---

## FAQ

**P: Posso modificar os nomes dos arquivos?**  
R: Prefira manter os nomes padrão, mas o importante é que você tenha os 3 logs + JSON/CSV + templates preenchidos.

**P: E se não conseguir executar a validação local?**  
R: Envie mesmo assim com os logs brutos. O coordenador processará.

**P: Qual é o melhor formato para os logs?**  
R: Texto puro UTF-8, com quebras de linha. Se salvo do Serial Monitor em Arduino IDE, estará certo.

**P: Posso compactar várias tentativas?**  
R: Prefira apenas a execução final bem-sucedida. Se teve múltiplas tentativas, use a melhor.

**P: Como saber se meu ZIP está certo?**  
R: Descompacte em outra pasta e verifique se contém tudo; se sim, está OK.

---

## Contato

Se tiver dúvidas durante preenchimento:
1. Consulte RESULTADOS_ESPERADOS.md (valores esperados)
2. Consulte TROUBLESHOOTING.md (problemas comuns)
3. Consulte LIMITES_DE_CLAIM.md (o que pode/não pode afirmar)

---

**Versão:** V8B2 · 2026-05-19
