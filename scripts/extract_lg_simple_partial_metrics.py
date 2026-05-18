import re
from pathlib import Path
import pandas as pd

log_path = Path("outputs/external_datasets/train_lg_simple_run.log")
out_csv = Path("outputs/external_datasets/lg_only_method_b_partial_metrics.csv")
out_md = Path("outputs/external_datasets/lg_only_method_b_partial_summary.md")

text = log_path.read_text(encoding="utf-8", errors="ignore")

rows = []
for m in re.finditer(r"Cell\s+(\d+):\s+R2=([-\d\.eE]+)", text):
    rows.append({
        "cell_id": int(m.group(1)),
        "R2": float(m.group(2)),
        "status": "partial_fold_completed"
    })

df = pd.DataFrame(rows).drop_duplicates(subset=["cell_id"], keep="last")

out_csv.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_csv, index=False)

if len(df) > 0:
    mean_r2 = df["R2"].mean()
    std_r2 = df["R2"].std() if len(df) > 1 else 0.0
    best = df.loc[df["R2"].idxmax()]
    worst = df.loc[df["R2"].idxmin()]
else:
    mean_r2 = std_r2 = 0
    best = worst = None

summary = [
    "# LG-only Method B Cross-cell - Resultado Parcial",
    "",
    "## Status",
    "LG_ONLY_METHOD_B_PARTIAL_DIAGNOSTIC",
    "",
    "## Escopo",
    "- Treino interrompido por tempo local.",
    "- Resultado NÃO é validação final completa.",
    "- Usar como diagnóstico preliminar de viabilidade e heterogeneidade entre células.",
    "",
    "## Métricas Parciais",
    f"- Folds concluídos: {len(df)}",
    f"- R2 médio parcial: {mean_r2:.4f}" if len(df) else "- R2 médio parcial: N/A",
    f"- R2 std parcial: {std_r2:.4f}" if len(df) else "- R2 std parcial: N/A",
]

if len(df) > 0:
    summary += [
        f"- Melhor célula: {int(best['cell_id'])} | R2={best['R2']:.4f}",
        f"- Pior célula: {int(worst['cell_id'])} | R2={worst['R2']:.4f}",
        "",
        "## Interpretação",
        "- O modelo LG-only com Method B aprende em parte das células.",
        "- A variação forte entre células indica heterogeneidade/cell-domain shift.",
        "- Próxima etapa recomendada: diagnosticar a pior célula e/ou usar amostragem controlada menor para completar todos os folds.",
    ]

out_md.write_text("\n".join(summary), encoding="utf-8")

print(f"OK: {out_csv}")
print(f"OK: {out_md}")
print(df)
