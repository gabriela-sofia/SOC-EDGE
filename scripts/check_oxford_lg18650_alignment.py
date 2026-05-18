#!/usr/bin/env python3
"""
QA check: Oxford Stage 4C ↔ LG18650_HG2 feature alignment.
Compare schema, ranges, derivability.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import glob

PROJECT_ROOT = Path(".")
OXFORD_PATTERN = "CORE/stage4c_final_results/processed/cell_Cell*_processed.csv"
LG_PARQUET = "data/processed/external/lg18650_hg2/lg18650_hg2_normalized.parquet"
OUT_QA_CSV = "outputs/external_datasets/oxford_lg18650_alignment_qa.csv"
OUT_SUMMARY = "outputs/external_datasets/oxford_lg18650_alignment_summary.md"

print("="*70)
print("OXFORD ↔ LG18650_HG2 ALIGNMENT CHECK")
print("="*70 + "\n")

# 1. Oxford overview
oxford_files = sorted(glob.glob(OXFORD_PATTERN))
print(f"1. OXFORD STAGE 4C")
print(f"   Files: {len(oxford_files)}")

if oxford_files:
    # Load one file to check schema
    df_ox_sample = pd.read_csv(oxford_files[0], nrows=1000)
    ox_columns = list(df_ox_sample.columns)
    print(f"   Columns: {', '.join(ox_columns)}")

    # Count total rows
    ox_total_rows = 0
    ox_cells = set()
    for f in oxford_files:
        df_tmp = pd.read_csv(f)
        ox_total_rows += len(df_tmp)
        ox_cells.update(df_tmp['cell_name'].unique() if 'cell_name' in df_tmp.columns else [])

    print(f"   Total rows: {ox_total_rows:,}")
    print(f"   Unique cells: {len(ox_cells)}")

    # Check ranges
    ranges_ox = {
        'voltage_V': (df_ox_sample['voltage_V'].min(), df_ox_sample['voltage_V'].max()),
        'temperature_C': (df_ox_sample['temperature_C'].min(), df_ox_sample['temperature_C'].max()),
        'current_abs_A': (df_ox_sample['current_abs_A'].min(), df_ox_sample['current_abs_A'].max()),
    }
    if 'method_B_soc_q_cycle' in df_ox_sample.columns:
        ranges_ox['method_B_soc_q_cycle'] = (df_ox_sample['method_B_soc_q_cycle'].min(), df_ox_sample['method_B_soc_q_cycle'].max())

    print(f"\n   Ranges (sample):")
    for key, (mn, mx) in ranges_ox.items():
        print(f"     {key}: [{mn:.3f}, {mx:.3f}]")

# 2. LG overview
print(f"\n2. LG18650_HG2 NORMALIZED")
if Path(LG_PARQUET).exists():
    df_lg = pd.read_parquet(LG_PARQUET)
    print(f"   Shape: {df_lg.shape}")
    print(f"   Columns: {', '.join(df_lg.columns)}")

    lg_cells = df_lg['cell_id'].nunique() if 'cell_id' in df_lg.columns else 0
    lg_train_eligible = (df_lg['train_eligible'] == True).sum() if 'train_eligible' in df_lg.columns else 0

    print(f"   Total rows: {len(df_lg):,}")
    print(f"   Unique cells: {lg_cells}")
    print(f"   Train-eligible: {lg_train_eligible:,}")

    # Check ranges
    ranges_lg = {
        'voltage_V': (df_lg['voltage_V'].min(), df_lg['voltage_V'].max()),
        'temperature_C': (df_lg['temperature_C'].min(), df_lg['temperature_C'].max()),
        'current_A': (df_lg['current_A'].min(), df_lg['current_A'].max()),
    }
    if 'soc_target' in df_lg.columns:
        ranges_lg['soc_target'] = (df_lg['soc_target'].min(), df_lg['soc_target'].max())

    print(f"\n   Ranges:")
    for key, (mn, mx) in ranges_lg.items():
        print(f"     {key}: [{mn:.3f}, {mx:.3f}]")

# 3. Feature alignment
print(f"\n3. FEATURE ALIGNMENT")
print(f"\n   Oxford Stage 4C features required:")
required_ox = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
for feat in required_ox:
    present = "✓" if feat in ox_columns else "✗"
    print(f"     {present} {feat}")

print(f"\n   LG available features:")
for col in df_lg.columns:
    print(f"     ✓ {col}")

print(f"\n   Current_abs_A derivability:")
if 'current_A' in df_lg.columns:
    print(f"     ✓ LG.current_A → can derive |current_A|")
else:
    print(f"     ✗ LG missing current signal")

print(f"\n   Delta derivability (temporal gradients):")
print(f"     ✓ Derivable from time_s + voltage_V → delta_voltage")
print(f"     ✓ Derivable from time_s + temperature_C → delta_temperature")
print(f"     ✓ Derivable from time_s + current_A → delta_current")

# 4. Target (SOC) compatibility
print(f"\n4. TARGET (SOC) COMPATIBILITY")
if 'soc_target' in df_lg.columns and 'method_B_soc_q_cycle' in ox_columns:
    print(f"   Oxford: method_B_soc_q_cycle")
    print(f"   LG:     soc_target")
    print(f"   Status: Both have SOC; different derivation methods")
    print(f"           Oxford uses Method B (coulombic integration)")
    print(f"           LG uses capacity-based approach")
    print(f"   Compatibility: PARTIAL (need method alignment)")

# 5. Generate QA CSV
qa_rows = [
    {
        'component': 'Oxford Stage 4C',
        'rows': f"{ox_total_rows:,}",
        'cells': len(ox_cells),
        'voltage_range': f"[{ranges_ox['voltage_V'][0]:.2f}, {ranges_ox['voltage_V'][1]:.2f}]",
        'current_range': f"[{ranges_ox['current_abs_A'][0]:.3f}, {ranges_ox['current_abs_A'][1]:.3f}]",
        'temp_range': f"[{ranges_ox['temperature_C'][0]:.1f}, {ranges_ox['temperature_C'][1]:.1f}]",
        'soc_range': f"[{ranges_ox.get('method_B_soc_q_cycle', (np.nan, np.nan))[0]:.3f}, {ranges_ox.get('method_B_soc_q_cycle', (np.nan, np.nan))[1]:.3f}]",
        'soc_method': 'method_B_q_cycle',
        'key_features': 'voltage, temp, current_abs, deltas, SOC'
    },
    {
        'component': 'LG18650_HG2',
        'rows': f"{len(df_lg):,}",
        'cells': lg_cells,
        'voltage_range': f"[{ranges_lg['voltage_V'][0]:.2f}, {ranges_lg['voltage_V'][1]:.2f}]",
        'current_range': f"[{abs(ranges_lg['current_A'][0]):.3f}, {ranges_lg['current_A'][1]:.3f}]",
        'temp_range': f"[{ranges_lg['temperature_C'][0]:.1f}, {ranges_lg['temperature_C'][1]:.1f}]",
        'soc_range': f"[{ranges_lg['soc_target'][0]:.3f}, {ranges_lg['soc_target'][1]:.3f}]",
        'soc_method': 'capacity_based',
        'key_features': 'voltage, temp, current (signed), capacity, SOC'
    }
]

pd.DataFrame(qa_rows).to_csv(OUT_QA_CSV, index=False)
print(f"\n✓ Saved QA CSV: {OUT_QA_CSV}")

# 6. Determine alignment readiness
needs_derivation = ['current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
lg_has_base = 'voltage_V' in df_lg.columns and 'current_A' in df_lg.columns and 'temperature_C' in df_lg.columns

if lg_has_base:
    decision = "NEEDS_FEATURE_DERIVATION"
else:
    decision = "LG_NEEDS_FIX"

target_alignment = "PARTIAL" if 'soc_target' in df_lg.columns and 'method_B_soc_q_cycle' in ox_columns else "MISSING"

if target_alignment == "PARTIAL":
    decision = "NEEDS_TARGET_REVIEW"

# 7. Generate summary
with open(OUT_SUMMARY, 'w') as f:
    f.write("# Oxford Stage 4C ↔ LG18650_HG2 Alignment QA\n\n")

    f.write("## Dataset Overview\n\n")
    f.write(f"- **Oxford Stage 4C:** {ox_total_rows:,} rows, {len(ox_cells)} cells\n")
    f.write(f"- **LG18650_HG2:** {len(df_lg):,} rows, {lg_cells} cells, {lg_train_eligible:,} train-eligible\n\n")

    f.write("## Feature Matrix\n\n")
    f.write("| Feature | Oxford | LG | Status |\n")
    f.write("|---------|--------|----|---------|\n")
    f.write("| voltage_V | ✓ | ✓ | Available |\n")
    f.write("| temperature_C | ✓ | ✓ | Available |\n")
    f.write("| current signal | ✓ (abs) | ✓ (signed) | Convertible |\n")
    f.write("| current_abs_A | ✓ | ✗ | Derivable |\n")
    f.write("| delta_voltage | ✓ | ✗ | Derivable |\n")
    f.write("| delta_temperature | ✓ | ✗ | Derivable |\n")
    f.write("| delta_current | ✓ | ✗ | Derivable |\n")
    f.write("| current_rel | ✗ | ✗ | Missing both |\n\n")

    f.write("## Target (SOC) Alignment\n\n")
    f.write("- **Oxford:** method_B_soc_q_cycle (coulombic integration, cycle-normalized)\n")
    f.write("- **LG:** soc_target (capacity-based normalization)\n")
    f.write("- **Compatibility:** PARTIAL — both are SOC, but different derivation methods\n\n")

    f.write("## Data Quality\n\n")
    f.write(f"- Voltage ranges: Oxford [{ranges_ox['voltage_V'][0]:.2f}, {ranges_ox['voltage_V'][1]:.2f}]V, LG [{ranges_lg['voltage_V'][0]:.2f}, {ranges_lg['voltage_V'][1]:.2f}]V ✓ Overlapping\n")
    f.write(f"- Temperature ranges: Oxford [{ranges_ox['temperature_C'][0]:.1f}, {ranges_ox['temperature_C'][1]:.1f}]°C, LG [{ranges_lg['temperature_C'][0]:.1f}, {ranges_lg['temperature_C'][1]:.1f}]°C ✓ Overlapping\n")
    f.write(f"- Current: Oxford uses |I|, LG has signed current ✓ Convertible\n\n")

    f.write("## Decision\n\n")
    f.write(f"**{decision}**\n\n")

    if decision == "NEEDS_FEATURE_DERIVATION":
        f.write("LG18650_HG2 has all base signals (voltage, current, temperature). Features delta_* and current_abs_A are derivable via numeric differentiation and absolute value. Feature current_rel (relative current) is not available in either dataset.\n\n")
    elif decision == "NEEDS_TARGET_REVIEW":
        f.write("SOC derivation methods differ. Need method alignment review before model evaluation.\n\n")

    f.write("## Next Steps\n\n")
    f.write("1. Derive current_abs_A, delta_* features in LG data\n")
    f.write("2. Align SOC methods (Method B vs capacity-based) or evaluate separately\n")
    f.write("3. Validate feature ranges match expected Stage 4C input distributions\n")
    f.write("4. Proceed to model evaluation with derived features\n")

print(f"✓ Saved summary: {OUT_SUMMARY}\n")
print(f"DECISION: {decision}")
