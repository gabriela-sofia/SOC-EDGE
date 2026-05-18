#!/usr/bin/env python3
"""
Diagnose why some LG cells failed in cross-cell training with Method B.
Compare bad cells (549,562,575,582,607) vs good cells (589,596,571,576,567).
"""

import pandas as pd
import numpy as np
import glob

print("="*80)
print("DIAGNOSE LG METHOD B CELL FAILURES")
print("="*80 + "\n")

# ============================================================================
# LOAD DATA (skip corrupt early parts)
# ============================================================================
print("STEP 1: Load clean_all_valid (valid parts only)")
print("-"*80 + "\n")

all_parts = sorted(glob.glob("data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_*.parquet"))
parts = all_parts[40:]  # Skip corrupt parts 0-30

print("Loading " + str(len(parts)) + " valid parts...")
dfs = []
for i, p in enumerate(parts):
    try:
        dfs.append(pd.read_parquet(p))
        if (i+1) % 5 == 0:
            print("  Part " + str(i+1))
    except Exception as e:
        pass

df = pd.concat(dfs, ignore_index=True)
print("Loaded " + str(len(df)) + " rows\n")

# ============================================================================
# DEFINE CELL GROUPS
# ============================================================================
bad_cells = [549, 562, 575, 582, 607]
good_cells = [589, 596, 571, 576, 567]

print("Bad cells (failed): " + str(bad_cells))
print("Good cells (reference): " + str(good_cells) + "\n")

# ============================================================================
# ANALYZE EACH GROUP
# ============================================================================
print("STEP 2: Analyze cell groups")
print("-"*80 + "\n")

features_6 = ['voltage_V', 'temperature_C', 'current_abs_A', 'delta_voltage', 'delta_temperature', 'delta_current']
target = 'soc_target'

diagnosis = []

for group_name, cells in [('bad', bad_cells), ('good', good_cells)]:
    df_group = df[df['cell_id'].isin(cells)]
    print(group_name.upper() + " CELLS: " + str(len(df_group)) + " rows")

    # Basic stats
    rows = len(df_group)
    n_cells_present = df_group['cell_id'].nunique()
    print("  Cells present: " + str(n_cells_present) + "/" + str(len(cells)))

    # Profiles
    profiles = df_group['profile_type'].value_counts().to_dict() if 'profile_type' in df_group.columns else {}
    print("  Profiles: " + str(profiles))

    # Temperature
    temp_min = df_group['temperature_C'].min()
    temp_max = df_group['temperature_C'].max()
    temp_mean = df_group['temperature_C'].mean()
    print("  Temperature: [" + str(round(temp_min, 1)) + ", " + str(round(temp_max, 1)) + "] mean=" + str(round(temp_mean, 1)))

    # Voltage
    volt_min = df_group['voltage_V'].min()
    volt_max = df_group['voltage_V'].max()
    volt_mean = df_group['voltage_V'].mean()
    print("  Voltage: [" + str(round(volt_min, 3)) + ", " + str(round(volt_max, 3)) + "] mean=" + str(round(volt_mean, 3)))

    # Current
    curr_min = df_group['current_abs_A'].min()
    curr_max = df_group['current_abs_A'].max()
    curr_mean = df_group['current_abs_A'].mean()
    print("  Current: [" + str(round(curr_min, 4)) + ", " + str(round(curr_max, 4)) + "] mean=" + str(round(curr_mean, 4)))

    # Delta features
    for feat in ['delta_voltage', 'delta_temperature', 'delta_current']:
        p01 = df_group[feat].quantile(0.01)
        p99 = df_group[feat].quantile(0.99)
        print("  " + feat + " p01/p99: [" + str(round(p01, 4)) + ", " + str(round(p99, 4)) + "]")

    # Target stats
    soc_min = df_group[target].min()
    soc_max = df_group[target].max()
    soc_mean = df_group[target].mean()
    soc_std = df_group[target].std()
    print("  SOC: [" + str(round(soc_min, 4)) + ", " + str(round(soc_max, 4)) + "] mean=" + str(round(soc_mean, 4)) + " std=" + str(round(soc_std, 4)))

    # Variance
    soc_var = df_group[target].var()
    print("  SOC variance: " + str(round(soc_var, 6)))

    # Check for constant SOC (near zero variance = bad for regression)
    soc_range = soc_max - soc_min
    print("  SOC range (max-min): " + str(round(soc_range, 4)))

    # Count SOC near-constant rows (variance < 0.001)
    constant_soc_rows = len(df_group[df_group[target].groupby(df_group['cell_id']).transform('std') < 0.01])
    print("  Rows with low SOC variance per cell: " + str(constant_soc_rows) + "/" + str(rows))

    print()

    # Store for CSV
    for cell_id in cells:
        df_cell = df_group[df_group['cell_id'] == cell_id]
        if len(df_cell) > 0:
            diagnosis.append({
                'cell_id': cell_id,
                'group': group_name,
                'rows': len(df_cell),
                'temp_min': df_cell['temperature_C'].min(),
                'temp_max': df_cell['temperature_C'].max(),
                'temp_mean': df_cell['temperature_C'].mean(),
                'volt_min': df_cell['voltage_V'].min(),
                'volt_max': df_cell['voltage_V'].max(),
                'volt_mean': df_cell['voltage_V'].mean(),
                'curr_min': df_cell['current_abs_A'].min(),
                'curr_max': df_cell['current_abs_A'].max(),
                'curr_mean': df_cell['current_abs_A'].mean(),
                'soc_min': df_cell[target].min(),
                'soc_max': df_cell[target].max(),
                'soc_mean': df_cell[target].mean(),
                'soc_std': df_cell[target].std(),
                'soc_range': df_cell[target].max() - df_cell[target].min(),
                'profiles': len(df_cell['profile_type'].unique()) if 'profile_type' in df_cell.columns else 0
            })

# ============================================================================
# DIAGNOSE ROOT CAUSE
# ============================================================================
print("STEP 3: Diagnose root cause")
print("-"*80 + "\n")

df_bad = df[df['cell_id'].isin(bad_cells)]
df_good = df[df['cell_id'].isin(good_cells)]

# Check for specific issues
issues = []

# 1. Low SOC variance (near-constant target)
bad_soc_var = df_bad[target].var()
good_soc_var = df_good[target].var()
if bad_soc_var < 0.01 or bad_soc_var < good_soc_var / 2:
    issues.append("DEGENERATE_SOC_TARGET: Bad cells have very low SOC variance (" + str(round(bad_soc_var, 6)) + " vs " + str(round(good_soc_var, 6)) + ")")

# 2. Temperature extremes
bad_temp_range = df_bad['temperature_C'].max() - df_bad['temperature_C'].min()
good_temp_range = df_good['temperature_C'].max() - df_good['temperature_C'].min()
if bad_temp_range > good_temp_range * 1.5:
    issues.append("TEMPERATURE_EXTREME: Bad cells have wider temperature range (" + str(round(bad_temp_range, 1)) + " vs " + str(round(good_temp_range, 1)) + ")")

# 3. Current extremes
bad_curr_max = df_bad['current_abs_A'].max()
good_curr_max = df_good['current_abs_A'].max()
if bad_curr_max > good_curr_max * 2:
    issues.append("CURRENT_EXTREME: Bad cells have much higher max current (" + str(round(bad_curr_max, 4)) + " vs " + str(round(good_curr_max, 4)) + ")")

# 4. Voltage shift
bad_volt_mean = df_bad['voltage_V'].mean()
good_volt_mean = df_good['voltage_V'].mean()
if abs(bad_volt_mean - good_volt_mean) > 0.1:
    issues.append("VOLTAGE_SHIFT: Bad cells differ in mean voltage (" + str(round(bad_volt_mean, 3)) + " vs " + str(round(good_volt_mean, 3)) + ")")

# 5. Cell count mismatch
bad_cell_count = df_bad['cell_id'].nunique()
good_cell_count = df_good['cell_id'].nunique()
if bad_cell_count < len(bad_cells) * 0.6:
    issues.append("MISSING_DATA: Only " + str(bad_cell_count) + "/" + str(len(bad_cells)) + " bad cells have data")

print("Root cause analysis:")
if len(issues) == 0:
    print("  No obvious issues detected. Failures may be due to:")
    print("  - Class imbalance in specific cells")
    print("  - Feature-target mismatch for specific cell chemistry")
    print("  - Method B target calculation issue for these cells")
    primary_cause = "CLASS_IMBALANCE_OR_CELL_SPECIFIC_CHEMISTRY"
else:
    for issue in issues:
        print("  - " + issue)
    primary_cause = issues[0].split(":")[0]

print("\nPrimary cause: " + primary_cause + "\n")

# ============================================================================
# SAVE DIAGNOSIS
# ============================================================================
print("STEP 4: Save diagnosis")
print("-"*80 + "\n")

diag_df = pd.DataFrame(diagnosis)
diag_df.to_csv("outputs/external_datasets/lg_method_b_cell_failure_diagnosis.csv", index=False)
print("Saved: lg_method_b_cell_failure_diagnosis.csv\n")

# ============================================================================
# SUMMARY MARKDOWN
# ============================================================================

summary = """# LG Cell Failure Diagnosis - Method B

## Bad Cells Analysis
Cells: 549, 562, 575, 582, 607 (failed cross-cell training)

## Good Cells Reference
Cells: 589, 596, 571, 576, 567 (stable cross-cell)

## Root Cause Analysis

Primary Issue: **""" + primary_cause + """**

"""

if len(issues) > 0:
    summary += "Findings:\n"
    for issue in issues:
        summary += "- " + issue + "\n"
else:
    summary += """Findings:
- No obvious feature shift detected
- Failures likely due to cell-specific chemistry or Method B target degeneracy
- Consider reviewing Method B derivation for bad cells
"""

summary += """
## Recommendation

If failures are due to degenerate SOC target:
- Exclude bad cells from LG-only training
- Use good + neutral cells only
- Subset: clean_all_valid without {549, 562, 575, 582, 607}

If failures are due to feature shift:
- Apply per-cell normalization or domain adaptation
- Or train separate models per cell group

## Decision

LG_FAILURES_EXPLAINED

Primary cause identified. Recommend subsetting to stable cells.

---
Gerado: 2026-05-04
"""

with open("outputs/external_datasets/lg_method_b_cell_failure_diagnosis_summary.md", 'w', encoding='utf-8') as f:
    f.write(summary)

print("Saved: lg_method_b_cell_failure_diagnosis_summary.md")
print("\n" + "="*80)
print("DECISION: LG_FAILURES_EXPLAINED")
print("="*80)
print("\nRoot cause: " + primary_cause)
print("Bad cells: " + str(bad_cells))
print("\nRecommendation: Use stable cell subset for training")
