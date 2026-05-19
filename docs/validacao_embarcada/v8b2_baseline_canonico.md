# Baseline Canônico V8B2

O baseline canônico V8B2 é a camada pública usada para auditar o pacote de replay embarcado do SOC Method B na ESP32.

## Escopo

O baseline V8B2 cobre replay embarcado com vetores versionados. Ele não cobre bancada com sensor físico real, campo, produção, operação 24/7 ou validação industrial.

## Conteúdo Auditável

- estrutura esperada do pacote;
- manifesto canônico em `embedded/handoff_v8b2/manifests/V8B2_PACKAGE_MANIFEST.json`;
- firmware, headers e vetores de replay;
- cenários e flags de anomalia;
- resultados versionados de GOLDEN, EXTENDED e ANOMALY;
- validador canônico.

## Validador Canônico

O caminho canônico é:

```powershell
python embedded/handoff_v8b2/validation/validate_esp32_v8b2.py --help
```

Não deve haver lógica duplicada em `embedded/handoff_v8b2/validate_esp32_v8b2.py`.

## Auditoria do Pacote

Para verificar a estrutura do pacote:

```powershell
python scripts/check_v8b2_package.py
```

O auditor retorna:

- `PASS` quando o manifesto, a estrutura e os arquivos obrigatórios estão presentes;
- `WARN` quando há duplicidade não canônica ou item não bloqueante;
- `FAIL` quando falta item crítico.

## Validação com Log ESP32

Para validar um log serial real retornado da ESP32:

```powershell
python scripts/run_v8b2_validation.py caminho/do/log.txt
```

Para definir uma pasta de saída:

```powershell
python scripts/run_v8b2_validation.py caminho/do/log.txt --output-dir results/v8b2_run
```

## Claims Permitidos

- O pacote V8B2 foi validado por replay embarcado na ESP32.
- GOLDEN, EXTENDED e ANOMALY têm status PASS no escopo V8B2.
- A paridade Python vs ESP32 é limitada aos vetores versionados e ao schema V8B2.

## Claims Proibidos

- Validado em campo.
- Pronto para produção.
- Sensor físico real validado no V8B2.
- Operação 24/7 validada.
- Diagnóstico operacional de degradação ou SOH.
- Predição de vida útil.
- Validação industrial.

## Relação com V8C

V8C é a próxima etapa de bancada com aquisição real ou semi-real. Um PASS no baseline V8B2 não substitui V8C.
