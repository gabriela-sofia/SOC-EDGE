# Especificação de Handoff ESP32

O handoff ESP32 deve conter:

- firmware principal;
- headers com pesos, scaler e vetores de replay;
- arquivos CSV de replay e referência;
- cenários de anomalia e flags esperadas;
- script de validação dos logs retornados;
- manifest de modelo e replay;
- template de resultados.

O executor deve devolver logs serial completos, métricas de latência, heap, flash quando disponível, identificação do hardware e observações de falhas.

O handoff é parte da metodologia: ele registra como a validação embarcada foi operacionalizada e como os resultados podem ser auditados.
