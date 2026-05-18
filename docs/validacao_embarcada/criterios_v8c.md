# Critérios V8C

Os critérios V8C se aplicam apenas à bancada com aquisição real ou semi-real.

## PASS

| Dimensão | Critério |
|---|---|
| Estabilidade | Sem crash ou travamento durante a janela definida |
| Serial | Log contínuo, recuperável e com schema consistente |
| Heap | Sem queda progressiva incompatível com execução estável |
| Latência | Inferência permanece dentro do limite definido antes do teste |
| Aquisição | V/T/I presentes, parseáveis e com unidades corretas |
| Coerência temporal | SOC não apresenta saltos incompatíveis sem evento registrado |
| Resets | Zero reset inesperado |

## WARN

| Dimensão | Condição |
|---|---|
| Serial | Perda curta de linhas, mas com recuperação e explicação |
| Sensor | Leituras suspeitas isoladas com flag e sem colapso do sistema |
| Heap | Oscilação sem tendência progressiva |
| Latência | Picos isolados sem ultrapassar limite operacional definido |
| Coerência temporal | Desvio pontual com causa plausível |

## FAIL

| Dimensão | Condição |
|---|---|
| Estabilidade | Crash, travamento ou reset inesperado |
| Serial | Log corrompido a ponto de impedir auditoria |
| Aquisição | V/T/I ausentes ou em unidade errada sem detecção |
| Heap | Queda progressiva ou fragmentação que compromete execução |
| Latência | Inferência consistentemente acima do limite definido |
| Coerência temporal | SOC incoerente de forma persistente |

## Interpretação

Um PASS em V8C permite afirmar validação de bancada. Não permite afirmar campo ou produção.
