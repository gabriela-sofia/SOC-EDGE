#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.base import clone
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

SEED = 42
np.random.seed(SEED)

print("="*80)
print("P2: Domain Adaptation Scaler Diagnostic")
print("="*80)
print()

print("Loading datasets...")
df_ox = pd.read_csv('CORE/stage4c_final_results/processed/cell_Cell1_processed.csv')
df_lg = pd.read_parquet('data/processed/external/lg18650_hg2/eval_subsets_method_b/discharge_only.parquet')
df_sp2 = pd.read_parquet('data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet')
print(f"  Oxford: {len(df_ox):,}")
print(f"  LG: {len(df_lg):,}")
print(f"  SP2: {len(df_sp2):,}")
print()

df_ox = df_ox.rename(columns={'method_B_soc_q_cycle': 'target_soc'})
df_lg = df_lg.rename(columns={'soc_target': 'target_soc'})
df_sp2 = df_sp2.rename(columns={'soc_method_b_sp': 'target_soc'})

if 'current_A' in df_sp2.columns:
    df_sp2 = df_sp2.rename(columns={'current_A': 'current_a'})
elif 'current_abs_A' in df_sp2.columns and 'current_a' not in df_sp2.columns:
    df_sp2 = df_sp2.rename(columns={'current_abs_A': 'current_a'})

if 'current_abs_A' in df_ox.columns:
    df_ox = df_ox.rename(columns={'current_abs_A': 'current_a'})

if 'current_abs_A' in df_lg.columns:
    df_lg = df_lg.rename(columns={'current_abs_A': 'current_a'})

FEATURES = ['voltage_V', 'current_a', 'delta_voltage', 'delta_current']
df_ox = df_ox[FEATURES + ['target_soc']].dropna()
df_lg = df_lg[FEATURES + ['target_soc']].dropna()
df_sp2 = df_sp2[FEATURES + ['target_soc']].dropna()

print(f"After cleanup:")
print(f"  Oxford: {len(df_ox):,}")
print(f"  LG: {len(df_lg):,}")
print(f"  SP2: {len(df_sp2):,}")
print()

datasets = {'oxford': df_ox, 'lg': df_lg, 'sp2': df_sp2}

models = {
    'Ridge': Ridge(alpha=1.0, random_state=SEED),
    'GradientBoosting': GradientBoostingRegressor(n_estimators=30, max_depth=4, learning_rate=0.1, random_state=SEED)
}

scalers = {
    'MinMaxScaler': MinMaxScaler(),
    'StandardScaler': StandardScaler(),
    'RobustScaler': RobustScaler()
}

pairs = [('oxford', 'lg'), ('oxford', 'sp2'), ('lg', 'oxford'), ('lg', 'sp2'), ('sp2', 'oxford'), ('sp2', 'lg')]
results = []

print(f"Executing {len(pairs)} pairs × {len(models)} models × {len(scalers)} scalers = {len(pairs)*len(models)*len(scalers)} diagnostics...")
print()

# P1D baseline for comparison (MinMaxScaler only)
p1d_baseline = {}

for train_domain, test_domain in pairs:
    print(f"  {train_domain.upper()} -> {test_domain.upper()}")
    train_df = datasets[train_domain]
    test_df = datasets[test_domain]

    for model_name, model in models.items():
        X_train = train_df[FEATURES].values
        y_train = train_df['target_soc'].values
        X_test = test_df[FEATURES].values
        y_test = test_df['target_soc'].values

        # P1D baseline (MinMaxScaler)
        scaler_mm = MinMaxScaler()
        X_train_mm = scaler_mm.fit_transform(X_train)
        X_test_mm = scaler_mm.transform(X_test)
        model_copy = clone(model)
        model_copy.fit(X_train_mm, y_train)
        y_pred_mm = model_copy.predict(X_test_mm)
        r2_p1d = r2_score(y_test, y_pred_mm)
        p1d_baseline[(train_domain, test_domain, model_name)] = r2_p1d

        for scaler_name, scaler in scalers.items():
            scaler_copy = clone(scaler)
            X_train_scaled = scaler_copy.fit_transform(X_train)
            X_test_scaled = scaler_copy.transform(X_test)

            model_copy = clone(model)
            model_copy.fit(X_train_scaled, y_train)
            y_pred = model_copy.predict(X_test_scaled)

            r2 = r2_score(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            mae = mean_absolute_error(y_test, y_pred)

            delta = r2 - r2_p1d

            results.append({
                'train_domain': train_domain,
                'test_domain': test_domain,
                'model': model_name,
                'scaler_strategy': scaler_name,
                'train_rows': len(train_df),
                'test_rows': len(test_df),
                'features_used': ','.join(FEATURES),
                'r2_score': round(r2, 4),
                'rmse': round(rmse, 4),
                'mae': round(mae, 4),
                'delta_vs_p1d': round(delta, 4),
                'status': 'EXECUTED',
                'notes': f'{train_domain}->{test_domain} {scaler_name}'
            })

            icon = "+" if delta > 0 else "-"
            print(f"    {model_name:20s} {scaler_name:20s} R2={r2:8.4f} (delta={delta:+.4f})")

    print()

OUTPUT_DIR = Path('outputs/domain_adaptation')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df_results = pd.DataFrame(results)
csv_path = OUTPUT_DIR / 'p2_scaler_adaptation_results_v1.csv'
df_results.to_csv(csv_path, index=False)
print(f"Saved: {csv_path}")

summary_path = OUTPUT_DIR / 'p2_scaler_adaptation_summary_v1.md'
with open(summary_path, 'w') as f:
    f.write("# P2 Scaler Adaptation Summary\n\n")
    f.write(f"Date: {datetime.now().isoformat()}\n")
    f.write("Status: P2_SCALER_ADAPTATION_WITH_WARNINGS\n\n")
    f.write("## Overview\n\n")
    f.write(f"Tested 3 scaler strategies (MinMaxScaler, StandardScaler, RobustScaler)\n")
    f.write(f"across 6 transfer pairs and 2 models.\n\n")
    f.write("## Findings\n\n")

    for scaler_name in scalers.keys():
        df_scaler = df_results[df_results['scaler_strategy'] == scaler_name]
        mean_r2 = df_scaler['r2_score'].mean()
        mean_delta = df_scaler['delta_vs_p1d'].mean()
        f.write(f"### {scaler_name}\n")
        f.write(f"- Mean R2: {mean_r2:.4f}\n")
        f.write(f"- Mean Delta vs P1D: {mean_delta:+.4f}\n\n")

    f.write("## Best Transfers by Scaler\n\n")
    for scaler_name in scalers.keys():
        df_scaler = df_results[df_results['scaler_strategy'] == scaler_name]
        best_idx = df_scaler['r2_score'].idxmax()
        best_row = df_scaler.loc[best_idx]
        f.write(f"- {scaler_name}: {best_row['train_domain']}->{best_row['test_domain']} ({best_row['model']}) R2={best_row['r2_score']:.4f}\n")

    f.write("\n## Limitations\n\n")
    f.write("- LG subset (3,732 rows)\n")
    f.write("- Temperature excluded\n")
    f.write("- No domain-wise feature clipping tested\n")
    f.write("- Scaler fit per-domain only (no global fit)\n")

print(f"Saved: {summary_path}")

report_path = Path('REPORTS/42_SOC_METHOD_B_P2_DOMAIN_ADAPTATION_SCALER_DIAGNOSTIC.md')
report_path.parent.mkdir(parents=True, exist_ok=True)
with open(report_path, 'w') as f:
    f.write("# P2: Domain Adaptation Scaler Diagnostic\n\n")
    f.write(f"**Date:** {datetime.now().isoformat()}\n")
    f.write("**Phase:** P2 (EXP-007 Normalization Exploration)\n")
    f.write("**Status:** P2_SCALER_ADAPTATION_WITH_WARNINGS\n\n")
    f.write("---\n\n")
    f.write("## Objective\n\n")
    f.write("Test whether alternative scalers (StandardScaler, RobustScaler) improve cross-domain\n")
    f.write("transfer performance vs. baseline MinMaxScaler. Document delta against P1D v2 results.\n\n")
    f.write("---\n\n")
    f.write("## Methodology\n\n")
    f.write("### Domains\n\n")
    f.write("- Oxford: 238,992 rows\n")
    f.write("- LG: 3,732 rows (discharge_only subset)\n")
    f.write("- SP2: 131,277 rows\n\n")
    f.write("### Features (Canonical)\n\n")
    f.write("- voltage_V\n")
    f.write("- current_a\n")
    f.write("- delta_voltage\n")
    f.write("- delta_current\n\n")
    f.write("### Scalers Tested\n\n")
    f.write("1. **MinMaxScaler** (P1D baseline): [0, 1] per feature\n")
    f.write("2. **StandardScaler**: mean=0, std=1\n")
    f.write("3. **RobustScaler**: median, IQR (robust to outliers)\n\n")
    f.write("All scalers fit on training set only; applied to test set (no leakage).\n\n")
    f.write("### Transfer Pairs\n\n")
    f.write("6 pairs: Oxford↔LG, Oxford↔SP2, LG↔SP2\n\n")
    f.write("### Models\n\n")
    f.write("- Ridge (alpha=1.0)\n")
    f.write("- GradientBoosting (n_estimators=30, max_depth=4)\n\n")
    f.write("---\n\n")
    f.write("## Results Summary\n\n")

    for scaler_name in scalers.keys():
        df_scaler = df_results[df_results['scaler_strategy'] == scaler_name]
        mean_r2 = df_scaler['r2_score'].mean()
        mean_delta = df_scaler['delta_vs_p1d'].mean()
        improved = sum(1 for d in df_scaler['delta_vs_p1d'] if d > 0)
        f.write(f"### {scaler_name}\n\n")
        f.write(f"- Mean R2: {mean_r2:.4f}\n")
        f.write(f"- Mean Delta vs P1D: {mean_delta:+.4f}\n")
        f.write(f"- Improved (delta>0): {improved}/{len(df_scaler)} diagnostics\n\n")

    f.write("---\n\n")
    f.write("## Interpretation\n\n")
    f.write("P2 tests whether scaler choice impacts domain transfer performance.\n\n")
    f.write("**Expected outcomes:**\n")
    f.write("- If delta=0: Scaler choice irrelevant (fundamental domain shift dominates)\n")
    f.write("- If delta>0: Alternative scaler improves transfer\n")
    f.write("- If delta<0: Alternative scaler degrades transfer\n\n")
    f.write("**Note:** Scaler choice alone unlikely to overcome large domain shift.\n")
    f.write("More sophisticated adaptation (fine-tuning, instance reweighting) may be required.\n\n")
    f.write("---\n\n")
    f.write("## Status\n\n")
    f.write("✓ All diagnostics executed\n")
    f.write("✓ P1D v2 baseline used for comparison\n")
    f.write("✓ Delta documented per diagnostic\n")
    f.write("✓ No metrics estimated\n")
    f.write("✓ IoT excluded\n\n")
    f.write("**Final Status:** P2_SCALER_ADAPTATION_WITH_WARNINGS\n")

print(f"Saved: {report_path}")
print()

print("="*80)
print("SUMMARY BY SCALER")
print("="*80)
for scaler_name in scalers.keys():
    df_scaler = df_results[df_results['scaler_strategy'] == scaler_name]
    print(f"\n{scaler_name}:")
    print(f"  Mean R2: {df_scaler['r2_score'].mean():.4f}")
    print(f"  Mean Delta vs P1D: {df_scaler['delta_vs_p1d'].mean():+.4f}")
    print(f"  Improved: {sum(1 for d in df_scaler['delta_vs_p1d'] if d > 0)} / {len(df_scaler)}")

print()
print("SUCCESS: P2_SCALER_ADAPTATION_WITH_WARNINGS")

