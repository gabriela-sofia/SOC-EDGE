# Protocolo de Execução ESP32

1. Abrir o firmware `embedded/handoff_v8b2/firmware/firmware_soc_v8b2_canonical.ino`.
2. Garantir que os headers em `embedded/handoff_v8b2/include/` estejam disponíveis no build.
3. Compilar para ESP32.
4. Executar os modos `GOLDEN`, `EXTENDED` e `ANOMALY` conforme o firmware.
5. Capturar log serial completo.
6. Validar o log com `embedded/handoff_v8b2/validation/validate_esp32_v8b2.py`.
7. Preencher o template de resultados.

Nenhum resultado deve ser resumido sem preservar o log ou a métrica que o sustenta.
