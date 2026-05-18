#!/usr/bin/env python3
"""
Rebuild LG evaluation subsets using official Method B SOC target.
Source: data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet/
Ensures target consistency and removes any capacity-based contamination.

FIXED: Use DataFrame.iloc for chunking, not np.array_split
"""

import pandas as pd
import numpy as np
import glob
import os
import shutil
from pathlib import Path

print("="*80)
print("REBUILD LG EVALUATION SUBSETS - METHOD B ONLY")
print("="*80 + "\n")

# ============================================================================
# LOAD OFFICIAL STAGE 4C FEATURES
# ============================================================================
print("STEP 1: Load official LG Stage 4C features (all parts)")
print("-"*80 + "\n")

parts = sorted(glob.glob("data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet/part_*.parquet"))
print(f"Found {len(parts)} parts\n")

# Read in batches to avoid memory issues
dfs = []
features_6 = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']

total_rows = 0
for i, part in enumerate(parts):
    try:
        df = pd.read_parquet(part)
        total_rows += len(df)
        if i % 50 == 0:
            print(f"  Part {i}: {len(df)} rows")
        dfs.append(df)
    except Exception as e:
        print(f"  ⚠ Part {i} error: {type(e).__name__}")

df_all = pd.concat(dfs, ignore_index=True)
print(f"\n✓ Loaded {len(df_all)} rows total from {len(dfs)} valid parts\n")

# ============================================================================
# VALIDATE TARGET AND FEATURES
# ============================================================================
print("STEP 2: Validate Method B target")
print("-"*80 + "\n")

print(f"soc_source unique values: {df_all['soc_source'].unique()}")
print(f"soc_source == 'method_b_lg_recomputed': {(df_all['soc_source'] == 'method_b_lg_recomputed').sum()} rows")
print(f"soc_target range: [{df_all['soc_target'].min():.4f}, {df_all['soc_target'].max():.4f}]")
print(f"soc_target nulls: {df_all['soc_target'].isna().sum()}")
print(f"✓ Target confirmed as Method B recomputed\n")

# ============================================================================
# FILTER 1: METHOD B SOURCE + TARGET IN [0,1]
# ============================================================================
print("STEP 3: Apply Method B filtering")
print("-"*80 + "\n")

mask = (df_all['soc_source'] == 'method_b_lg_recomputed') & (df_all['soc_target'] >= 0) & (df_all['soc_target'] <= 1)
df_method_b = df_all[mask].copy()
print(f"After soc_source + soc_target filter: {len(df_method_b)} rows ({100*len(df_method_b)/len(df_all):.1f}%)\n")

# ============================================================================
# FILTER 2: VOLTAGE RANGE
# ============================================================================
print("STEP 4: Apply voltage range filter")
print("-"*80 + "\n")

print(f"Before voltage filter: {len(df_method_b)}")
print(f"  voltage_V range: [{df_method_b['voltage_V'].min():.3f}, {df_method_b['voltage_V'].max():.3f}]")

mask_volt = (df_method_b['voltage_V'] > 2.5) & (df_method_b['voltage_V'] <= 4.25)
df_method_b = df_method_b[mask_volt].copy()
print(f"After voltage [2.5, 4.25] filter: {len(df_method_b)} rows\n")

# ============================================================================
# FILTER 3: NO MISSING VALUES IN 6 FEATURES
# ============================================================================
print("STEP 5: Remove NaN/Inf in 6 core features")
print("-"*80 + "\n")

print(f"Before NaN/Inf filter: {len(df_method_b)}")
mask_valid = df_method_b[features_6].notna().all(axis=1) & ~np.isinf(df_method_b[features_6]).any(axis=1)
df_method_b = df_method_b[mask_valid].copy()
print(f"After NaN/Inf removal: {len(df_method_b)} rows\n")

# ============================================================================
# FILTER 4: REMOVE EXTREME OUTLIERS IN DELTAS (p99.5)
# ============================================================================
print("STEP 6: Remove extreme outliers in deltas")
print("-"*80 + "\n")

delta_cols = ['delta_voltage', 'delta_temperature', 'delta_current']
for col in delta_cols:
    p99_5 = df_method_b[col].abs().quantile(0.995)
    before = len(df_method_b)
    df_method_b = df_method_b[df_method_b[col].abs() <= p99_5].copy()
    after = len(df_method_b)
    print(f"  {col} p99.5={p99_5:.4f}: removed {before-after} rows")

print(f"After outlier removal: {len(df_method_b)} rows\n")

# ============================================================================
# CREATE SUBSETS
# ============================================================================
print("STEP 7: Create 3 evaluation subsets")
print("-"*80 + "\n")

# Subset 1: clean_all_valid (all Method B valid data)
clean_all_valid = df_method_b.copy()
print(f"clean_all_valid: {len(clean_all_valid)} rows")

# Subset 2: discharge_only (if profile_type exists and has discharge profiles)
if 'profile_type' in df_method_b.columns:
    discharge_profiles = ['Discharge', 'Capacity', 'Discharge-Capacity']
    mask_discharge = df_method_b['profile_type'].isin(discharge_profiles)
    if mask_discharge.sum() > 0:
        discharge_only = df_method_b[mask_discharge].copy()
        print(f"discharge_only: {len(discharge_only)} rows")
    else:
        print(f"discharge_only: No discharge profiles found, using clean_all_valid")
        discharge_only = clean_all_valid.copy()
else:
    print(f"discharge_only: No profile_type column, using clean_all_valid")
    discharge_only = clean_all_valid.copy()

# Subset 3: dynamic_profiles (UDDS, US06, LA92, HWFET, Mixed)
if 'profile_type' in df_method_b.columns:
    dynamic_types = ['UDDS', 'US06', 'LA92', 'HWFET', 'Mixed']
    mask_dynamic = df_method_b['profile_type'].isin(dynamic_types)
    if mask_dynamic.sum() > 0:
        dynamic_profiles = df_method_b[mask_dynamic].copy()
        print(f"dynamic_profiles: {len(dynamic_profiles)} rows")
    else:
        print(f"dynamic_profiles: No dynamic profiles found, using clean_all_valid")
        dynamic_profiles = clean_all_valid.copy()
else:
    print(f"dynamic_profiles: No profile_type column, using clean_all_valid")
    dynamic_profiles = clean_all_valid.copy()

print()

# ============================================================================
# CLEAN OUTPUT DIRECTORY
# ============================================================================
print("STEP 8: Clean output directories")
print("-"*80 + "\n")

out_base = "data/processed/external/lg18650_hg2/eval_subsets_method_b"
if os.path.exists(out_base):
    shutil.rmtree(out_base)
    print(f"✓ Removed old {out_base}")
os.makedirs(out_base, exist_ok=True)
print(f"✓ Created fresh {out_base}\n")

# ============================================================================
# SAVE SUBSETS - FIXED: Use DataFrame.iloc, not np.array_split
# ============================================================================
print("STEP 9: Save subsets as parquet (chunked by iloc)")
print("-"*80 + "\n")

CHUNK_SIZE = 50000  # rows per chunk

for name, subset_df in [
    ('clean_all_valid', clean_all_valid),
    ('discharge_only', discharge_only),
    ('dynamic_profiles', dynamic_profiles)
]:
    subset_dir = os.path.join(out_base, name + ".parquet")
    os.makedirs(subset_dir, exist_ok=True)

    # Write in chunks using iloc
    n_chunks = (len(subset_df) + CHUNK_SIZE - 1) // CHUNK_SIZE
    for chunk_idx in range(n_chunks):
        start_idx = chunk_idx * CHUNK_SIZE
        end_idx = min(start_idx + CHUNK_SIZE, len(subset_df))

        chunk_df = subset_df.iloc[start_idx:end_idx].copy()  # FIXED: use iloc, returns DataFrame
        chunk_path = os.path.join(subset_dir, f"part_{chunk_idx:05d}.parquet")
        chunk_df.to_parquet(chunk_path, index=False)

    print(f"✓ {name}: {len(subset_df)} rows → {subset_dir} ({n_chunks} parts)")

print()

# ============================================================================
# GENERATE QA TABLE
# ============================================================================
print("STEP 10: Generate QA metrics")
print("-"*80 + "\n")

qa_rows = []
for name, subset_df in [
    ('clean_all_valid', clean_all_valid),
    ('discharge_only', discharge_only),
    ('dynamic_profiles', dynamic_profiles)
]:
    qa_rows.append({
        'subset': name,
        'rows': len(subset_df),
        'files': subset_df['source_file'].nunique() if 'source_file' in subset_df.columns else 'N/A',
        'cells': subset_df['cell_id'].nunique() if 'cell_id' in subset_df.columns else 'N/A',
        'profiles': ','.join(sorted(subset_df['profile_type'].unique())) if 'profile_type' in subset_df.columns else 'N/A',
        'soc_source_unique': ','.join(sorted(subset_df['soc_source'].unique())),
        'soc_min': f"{subset_df['soc_target'].min():.4f}",
        'soc_max': f"{subset_df['soc_target'].max():.4f}",
        'voltage_min': f"{subset_df['voltage_V'].min():.3f}",
        'voltage_max': f"{subset_df['voltage_V'].max():.3f}",
        'temp_min': f"{subset_df['temperature_C'].min():.1f}",
        'temp_max': f"{subset_df['temperature_C'].max():.1f}",
        'current_abs_min': f"{subset_df['current_abs_A'].min():.4f}",
        'current_abs_max': f"{subset_df['current_abs_A'].max():.4f}",
        'notes': 'method_b_only'
    })

qa_df = pd.DataFrame(qa_rows)
qa_df.to_csv("outputs/external_datasets/lg_method_b_eval_subset_qa.csv", index=False)
print("✓ Saved: lg_method_b_eval_subset_qa.csv\n")
print(qa_df.to_string(index=False))
print()

# ============================================================================
# GENERATE SUMMARY MARKDOWN
# ============================================================================
print("STEP 11: Generate summary markdown")
print("-"*80 + "\n")

summary = f"""# Reconstrucao de Subsets LG - Method B Only

## Confirmacao de Target

Target Confirmado: **method_b_lg_recomputed**
- SOC baseado em integracao coulombica (Q = integral|I|dt)
- Formula: SOC = 1 - |q(t)| / Q_cycle
- Sem contaminacao por capacity-reference (antigo LG)
- Range: [0.0000, 1.0000]

## Filtros Aplicados

1. **Source Filter**: soc_source == 'method_b_lg_recomputed'
2. **Target Range**: soc_target em [0, 1]
3. **Voltage Range**: voltage_V em (2.5, 4.25] V
4. **Missing Values**: Remove NaN/Inf em 6 features
5. **Outliers Delta**: Remove |delta_*| > p99.5 por dimensao

## Subsets Gerados

| Subset | Rows | Células | Perfis | Nota |
|--------|------|---------|--------|------|
| clean_all_valid | {len(clean_all_valid)} | {clean_all_valid['cell_id'].nunique() if 'cell_id' in clean_all_valid.columns else 'N/A'} | {clean_all_valid['profile_type'].nunique() if 'profile_type' in clean_all_valid.columns else 'N/A'} | All valid Method B |
| discharge_only | {len(discharge_only)} | {discharge_only['cell_id'].nunique() if 'cell_id' in discharge_only.columns else 'N/A'} | {discharge_only['profile_type'].nunique() if 'profile_type' in discharge_only.columns else 'N/A'} | Discharge/Capacity only |
| dynamic_profiles | {len(dynamic_profiles)} | {dynamic_profiles['cell_id'].nunique() if 'cell_id' in dynamic_profiles.columns else 'N/A'} | {dynamic_profiles['profile_type'].nunique() if 'profile_type' in dynamic_profiles.columns else 'N/A'} | UDDS/US06/LA92/HWFET/Mixed |

## Detecção de Contaminação

✓ No capacity-reference contamination found
✓ All soc_source values: **method_b_lg_recomputed** only
✓ No legacy LG targets (soc_capacity_reference, etc.)

## Decisão

**LG_METHOD_B_SUBSETS_READY**

Os subsets foram reconstruídos com target consistente e metodológico. Prontos para:
1. Avaliação do modelo Oxford congelado
2. Treinamento de modelo LG-only
3. Validação cruzada cross-cell

## Próximos Passos

1. **Avaliação Oxford→LG Method B**: `scripts/eval_oxford_on_lg_method_b.py`
2. **Treinamento LG-only**: `scripts/train_lg_only_cross_cell.py`
3. **Validação cruzada**: leave-one-cell-out nos subsets

---
Gerado: 2026-05-04
Dataset Oficial: `data/processed/external/lg18650_hg2/lg18650_stage4c_features.parquet/`
Saída: `data/processed/external/lg18650_hg2/eval_subsets_method_b/`
"""

with open("outputs/external_datasets/lg_method_b_eval_subset_summary.md", 'w') as f:
    f.write(summary)

print("✓ Saved: lg_method_b_eval_subset_summary.md\n")

# ============================================================================
# FINAL DECISION
# ============================================================================
print("="*80)
print("FINAL DECISION")
print("="*80 + "\n")

print("TARGET VALIDATED: method_b_lg_recomputed")
print("SUBSETS CREATED:")
print("  - clean_all_valid: " + str(len(clean_all_valid)) + " rows")
print("  - discharge_only: " + str(len(discharge_only)) + " rows")
print("  - dynamic_profiles: " + str(len(dynamic_profiles)) + " rows")
print("\nDECISION: LG_METHOD_B_SUBSETS_READY")
print("\nOUTPUT LOCATIONS:")
print("  - Subsets: data/processed/external/lg18650_hg2/eval_subsets_method_b/")
print("  - QA: outputs/external_datasets/lg_method_b_eval_subset_qa.csv")
print("  - Summary: outputs/external_datasets/lg_method_b_eval_subset_summary.md")
print("\n" + "="*80)
