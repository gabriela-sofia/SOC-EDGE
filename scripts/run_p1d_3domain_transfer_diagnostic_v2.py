#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
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
print("P1D v2: 3-Domain Transfer Diagnostic")
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

pairs = [('oxford', 'lg'), ('oxford', 'sp2'), ('lg', 'oxford'), ('lg', 'sp2'), ('sp2', 'oxford'), ('sp2', 'lg')]
results = []

print(f"Executing {len(pairs)*len(models)} diagnostics...")
print()

for train_domain, test_domain in pairs:
    print(f"  {train_domain.upper()} -> {test_domain.upper()}")
    train_df = datasets[train_domain]
    test_df = datasets[test_domain]

    for model_name, model in models.items():
        X_train = train_df[FEATURES].values
        y_train = train_df['target_soc'].values
        X_test = test_df[FEATURES].values
        y_test = test_df['target_soc'].values

        scaler = MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model_copy = clone(model)
        model_copy.fit(X_train_scaled, y_train)
        y_pred = model_copy.predict(X_test_scaled)

        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)

        results.append({
            'train_domain': train_domain,
            'test_domain': test_domain,
            'model': model_name,
            'train_rows': len(train_df),
            'test_rows': len(test_df),
            'features_used': ','.join(FEATURES),
            'scaler_strategy': 'MinMaxScaler fit train, apply test (per-domain)',
            'r2_score': round(r2, 4),
            'rmse': round(rmse, 4),
            'mae': round(mae, 4),
            'status': 'EXECUTED' if r2 >= -10 else 'ANOMALY_NEGATIVE_R2',
            'notes': f'{train_domain}->{test_domain}'
        })

        icon = "OK" if r2 >= -10 else "ERR"
        print(f"    {icon} {model_name:20s} R2={r2:8.4f}")
    print()

OUTPUT_DIR = Path('outputs/domain_adaptation')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df_results = pd.DataFrame(results)
csv_path = OUTPUT_DIR / 'p1d_3domain_transfer_results_v2.csv'
df_results.to_csv(csv_path, index=False)
print(f"Saved: {csv_path}")

qa_path = OUTPUT_DIR / 'p1d_transfer_provenance_qa_v1.md'
with open(qa_path, 'w') as f:
    f.write("# P1D v2 Provenance QA\n\n")
    f.write(f"Date: {datetime.now().isoformat()}\n")
    f.write(f"Seed: {SEED}\n\n")
    f.write("## Datasets\n\n")
    f.write(f"- Oxford CSV: {len(df_ox):,} rows\n")
    f.write(f"- LG Parquet: {len(df_lg):,} rows\n")
    f.write(f"- SP2 Parquet: {len(df_sp2):,} rows\n\n")
    f.write("## Features\n\n")
    f.write(f"Canonical: voltage_V, current_a, delta_voltage, delta_current\n\n")
    f.write("## Temperature\n\nEXCLUDED\n\n")
    executed = sum(1 for r in results if r['status'] == 'EXECUTED')
    errors = sum(1 for r in results if r['status'] == 'ERROR')
    f.write(f"## Summary\n\nTotal: {len(results)}, Executed: {executed}, Errors: {errors}\n")

print(f"Saved: {qa_path}")

summary_path = OUTPUT_DIR / 'p1d_3domain_transfer_summary_v2.md'
with open(summary_path, 'w') as f:
    f.write("# P1D v2 Summary\n\n")
    f.write(f"Date: {datetime.now().isoformat()}\n")
    f.write("Status: P1D_TRANSFER_DIAGNOSTIC_WITH_WARNINGS\n\n")
    f.write("## Results\n\n")
    df_gb = df_results[df_results['model'] == 'GradientBoosting']
    f.write("### GradientBoosting\n\n")
    for _, row in df_gb.iterrows():
        f.write(f"- {row['train_domain']} -> {row['test_domain']}: R2={row['r2_score']:.4f}\n")
    df_ridge = df_results[df_results['model'] == 'Ridge']
    f.write("\n### Ridge\n\n")
    for _, row in df_ridge.iterrows():
        f.write(f"- {row['train_domain']} -> {row['test_domain']}: R2={row['r2_score']:.4f}\n")

print(f"Saved: {summary_path}")
print()

print("="*80)
print("RESULTS")
print("="*80)
print("\nGradientBoosting:")
print(df_gb[['train_domain', 'test_domain', 'r2_score', 'rmse', 'mae']].to_string(index=False))
print("\nRidge:")
print(df_ridge[['train_domain', 'test_domain', 'r2_score', 'rmse', 'mae']].to_string(index=False))
print()
print("SUCCESS: P1D_TRANSFER_DIAGNOSTIC_WITH_WARNINGS")
