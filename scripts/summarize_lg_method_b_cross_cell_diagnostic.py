from pathlib import Path
import pandas as pd

metrics_path = Path("outputs/external_datasets/lg_only_method_b_stable_cells_metrics.csv")
out_csv = Path("outputs/external_datasets/lg_method_b_cell_group_summary.csv")
out_md = Path("outputs/external_datasets/lg_method_b_cross_cell_interpretation_summary.md")

df = pd.read_csv(metrics_path)
df["test_cell"] = df["test_cell"].astype(int)

residual_bad = {551, 555, 593}
ood_prior = {549, 562, 575, 582, 607}

def classify(cell, r2):
    if cell in residual_bad:
        return "residual_failure_cell"
    if r2 >= 0.60:
        return "stable_good_generalization"
    if r2 >= 0.30:
        return "moderate_generalization"
    return "weak_or_failure"

df["cell_group"] = df.apply(lambda r: classify(int(r["test_cell"]), float(r["R2"])), axis=1)

summary = (
    df.groupby("cell_group")
    .agg(
        cells=("test_cell", "count"),
        r2_mean=("R2", "mean"),
        r2_std=("R2", "std"),
        mae_mean=("MAE", "mean"),
        rmse_mean=("RMSE", "mean"),
        best_r2=("R2", "max"),
        worst_r2=("R2", "min"),
    )
    .reset_index()
)

stable_core = df[~df["test_cell"].isin(residual_bad)]
stable_core_r2_mean = stable_core["R2"].mean()
stable_core_r2_median = stable_core["R2"].median()
stable_core_mae_mean = stable_core["MAE"].mean()
stable_core_rmse_mean = stable_core["RMSE"].mean()

out_csv.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(out_csv, index=False)

md = f"""# LG Method B Cross-cell - Interpretacao Final Diagnostica

## Status
LG_METHOD_B_LEARNABLE_WITH_CELL_DOMAIN_SHIFT

## Base
- Dataset: LG18650_HG2
- Target: soc_target = method_b_lg_recomputed
- Features: voltage_V, temperature_C, current_abs_A, delta_voltage, delta_temperature, delta_current
- Avaliacao: leave-one-cell-out balanceado
- Observacao: resultado diagnostico, nao full training 4.8M rows

## Resultado stable-cells
- Celulas usadas: {len(df)}
- R2 medio: {df["R2"].mean():.4f}
- MAE medio: {df["MAE"].mean():.4f}
- RMSE medio: {df["RMSE"].mean():.4f}
- Melhor celula: {int(df.loc[df["R2"].idxmax(), "test_cell"])} | R2={df["R2"].max():.4f}
- Pior celula: {int(df.loc[df["R2"].idxmin(), "test_cell"])} | R2={df["R2"].min():.4f}

## Stable-core sensitivity
- Celulas removidas por falha residual: {sorted(residual_bad)}
- Celulas restantes: {len(stable_core)}
- R2 medio stable-core: {stable_core_r2_mean:.4f}
- R2 mediano stable-core: {stable_core_r2_median:.4f}
- MAE medio stable-core: {stable_core_mae_mean:.4f}
- RMSE medio stable-core: {stable_core_rmse_mean:.4f}

## Interpretacao
- O Method B foi transferido para o LG sem usar target capacity-based original.
- O target e aprendivel em um nucleo expressivo de celulas.
- As falhas residuais indicam cell-domain shift interno, nao invalidacao do target.
- Resultado deve ser reportado como validacao externa diagnostica e analise de limitacao.

## Decisao
USE_AS_METHOD_B_EXTERNAL_DIAGNOSTIC
"""

out_md.write_text(md, encoding="utf-8")

print(f"OK: {out_csv}")
print(f"OK: {out_md}")
print(summary)
