#!/usr/bin/env python3
"""Fix summary markdown with proper UTF-8 encoding (no special chars)."""

import pandas as pd

qa = pd.read_csv("outputs/external_datasets/lg_method_b_eval_subset_qa.csv")

summary = """# Rebuild LG Method B Subsets - COMPLETE

## Target Confirmado
method_b_lg_recomputed (coulombic SOC, sem contaminacao capacity-reference)

## Subsets Criados

| Subset | Rows | Celulas | Perfis |
|--------|------|---------|--------|
"""

for _, row in qa.iterrows():
    summary += f"| {row['subset']} | {row['rows']} | {row['cells']} | {row['profiles']} |\n"

summary += """
## Decisao

LG_METHOD_B_SUBSETS_READY

Todos 3 subsets Method B criados com sucesso. Sem contaminacao de target capacity-based.

## Proximo Passo

Treinar modelo LG-only com validacao cross-cell usando clean_all_valid.

---
Gerado: 2026-05-04
"""

with open("outputs/external_datasets/lg_method_b_eval_subset_summary.md", 'w', encoding='utf-8') as f:
    f.write(summary)

print("OK: lg_method_b_eval_subset_summary.md salvo com UTF-8")
