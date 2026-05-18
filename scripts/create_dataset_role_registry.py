#!/usr/bin/env python3
"""
Create a methodological registry of all datasets in the project.
Classify each by scientific role, primary use, and readiness.
"""

import pandas as pd
from pathlib import Path
import os

PROJECT_ROOT = Path(".")
OUT_CSV = "outputs/external_datasets/external_dataset_role_registry.csv"
OUT_MD = "outputs/external_datasets/external_dataset_role_registry.md"

print("="*70)
print("DATASET ROLE REGISTRY")
print("="*70 + "\n")

# Define all datasets with their metadata
datasets = [
    {
        'dataset_name': 'CORE (Oxford Stage 4C)',
        'path': 'CORE/stage4c_final_results/processed/',
        'scientific_role': 'official_baseline',
        'primary_use': 'Model training reference, Stage 4C feature spec',
        'secondary_use': 'Cross-dataset alignment validation',
        'can_train_soc': False,  # Baseline, not for direct training
        'can_validate_soc': True,
        'can_support_soh': False,
        'can_support_iot': False,
        'can_support_urban_motivation': False,
        'next_required_action': 'Already in use for alignment validation',
        'status': 'ACTIVE',
        'reason': '8 cells, 1.46M rows, Stage 4C features, coulombic SOC'
    },
    {
        'dataset_name': 'LG_HG2_Original_Dataset_McMasterUniversity',
        'path': 'LG_HG2_Original_Dataset_McMasterUniversity_Jan_2020/',
        'scientific_role': 'soc_external_validation_raw',
        'primary_use': 'Raw source for LG18650_HG2 normalized dataset',
        'secondary_use': 'Schema verification, data quality audits',
        'can_train_soc': False,
        'can_validate_soc': False,
        'can_support_soh': False,
        'can_support_iot': False,
        'can_support_urban_motivation': False,
        'next_required_action': 'Keep as historical reference only',
        'status': 'REFERENCE',
        'reason': '208 CSV files, raw format, already normalized to CORE/parquet'
    },
    {
        'dataset_name': 'LG_HG2_Prepared_Dataset_McMasterUniversity',
        'path': 'LG_HG2_Prepared_Dataset_McMasterUniversity_Jan_2020/',
        'scientific_role': 'soc_external_validation_prepared',
        'primary_use': 'Pre-normalized intermediate (not used; prefer our normalization)',
        'secondary_use': 'Schema comparison, verification only',
        'can_train_soc': False,
        'can_validate_soc': False,
        'can_support_soh': False,
        'can_support_iot': False,
        'can_support_urban_motivation': False,
        'next_required_action': 'Archive; use data/processed/external/lg18650_hg2 instead',
        'status': 'SUPERSEDED',
        'reason': 'Our normalized version (parquet) is the canonical form'
    },
    {
        'dataset_name': 'LG18650_HG2_Normalized (Canonical)',
        'path': 'data/processed/external/lg18650_hg2/lg18650_hg2_normalized.parquet/',
        'scientific_role': 'soc_external_validation_canonical',
        'primary_use': 'External SOC validation (Discharge profiles only)',
        'secondary_use': 'Cross-dataset feature derivation reference',
        'can_train_soc': True,
        'can_validate_soc': True,
        'can_support_soh': False,
        'can_support_iot': False,
        'can_support_urban_motivation': False,
        'next_required_action': 'Derive current_abs_A, delta features; use Discharge subset for eval',
        'status': 'ACTIVE',
        'reason': '5.41M rows, 23 cells, normalized parquet; Discharge profiles EXCELLENT compatibility'
    },
    {
        'dataset_name': 'PoliMi-TUB dataset',
        'path': 'PoliMi-TUB dataset - LG 18650HE4 Li-Ion Battery.zip',
        'scientific_role': 'soc_soh_external_validation',
        'primary_use': 'External SOC validation (different cell chemistry, same form factor)',
        'secondary_use': 'SOH degradation tracking, cycle counting',
        'can_train_soc': False,
        'can_validate_soc': True,
        'can_support_soh': True,
        'can_support_iot': False,
        'can_support_urban_motivation': False,
        'next_required_action': 'Normalize and schema-align to Stage 4C (after LG validation complete)',
        'status': 'PENDING_NORMALIZATION',
        'reason': 'HE4 chemistry (similar but not identical to HG2); provides SOH validation data'
    },
    {
        'dataset_name': 'CALCE SP (Stanford/Maryland)',
        'path': 'SP*_Initial_capacity*, SP*_LC_OCV*, SP*_DST/FUDS/US06/BJDST',
        'scientific_role': 'ocv_dynamic_profile_soh_auxiliary',
        'primary_use': 'OCV curves per temperature, dynamic drive cycles, SOH monitoring',
        'secondary_use': 'Feature engineering (OCV-based features), capacity fade tracking',
        'can_train_soc': False,
        'can_validate_soc': False,
        'can_support_soh': True,
        'can_support_iot': True,
        'can_support_urban_motivation': False,
        'next_required_action': 'Extract OCV templates by temperature; use for feature engineering in Stage 5',
        'status': 'PENDING_ANALYSIS',
        'reason': '24 SP datasets, multi-temperature, multi-profile (DST, FUDS, US06, BJDST)'
    },
    {
        'dataset_name': 'BatteryML-main',
        'path': 'BatteryML-main.zip',
        'scientific_role': 'benchmark_standardization_reference',
        'primary_use': 'Benchmark comparison, standardized metrics, literature baseline',
        'secondary_use': 'Feature engineering patterns, model architecture reference',
        'can_train_soc': False,
        'can_validate_soc': False,
        'can_support_soh': False,
        'can_support_iot': False,
        'can_support_urban_motivation': False,
        'next_required_action': 'Use for post-deployment performance comparison (Stage 6+)',
        'status': 'REFERENCE',
        'reason': 'External repository; benchmark for model generalization'
    },
    {
        'dataset_name': 'FNN xEV Li-ion SOC Estimator Script',
        'path': 'FNN_xEV_Li_ion_SOC_EstimatorScript_Jan_2020.mlx',
        'scientific_role': 'literature_baseline_reference',
        'primary_use': 'Literature method comparison, baseline architecture',
        'secondary_use': 'Feature selection insights, performance target definition',
        'can_train_soc': False,
        'can_validate_soc': False,
        'can_support_soh': False,
        'can_support_iot': False,
        'can_support_urban_motivation': False,
        'next_required_action': 'Implement as comparative baseline in Stage 6 model evaluation',
        'status': 'REFERENCE',
        'reason': '2020 published method; FNN-based SOC estimation, good baseline'
    },
    {
        'dataset_name': 'energy-harvesting-dataset-master',
        'path': 'energy-harvesting-dataset-master.zip',
        'scientific_role': 'iot_autonomy_context_motivation',
        'primary_use': 'IoT power budget context, energy harvesting scenarios',
        'secondary_use': 'Duty cycle patterns for embedded system design',
        'can_train_soc': False,
        'can_validate_soc': False,
        'can_support_soh': False,
        'can_support_iot': True,
        'can_support_urban_motivation': False,
        'next_required_action': 'Analyze power profiles; inform ESP32 sampling strategy (Stage 5)',
        'status': 'PENDING_ANALYSIS',
        'reason': 'Real IoT workloads; validates embedded runtime assumptions'
    },
    {
        'dataset_name': 'dccpubliclighting',
        'path': 'dccpubliclighting*.csv',
        'scientific_role': 'urban_street_lighting_context_motivation',
        'primary_use': 'Smart city street lighting demand patterns',
        'secondary_use': 'Urban deployment scenarios, duty cycle realism',
        'can_train_soc': False,
        'can_validate_soc': False,
        'can_support_soh': False,
        'can_support_iot': True,
        'can_support_urban_motivation': True,
        'next_required_action': 'Correlate with LG/Oxford discharge patterns; validate real-world relevance',
        'status': 'PENDING_ANALYSIS',
        'reason': 'Urban smart city use case; grounds technical choices in real deployment context'
    },
]

# Create DataFrame and save CSV
df_registry = pd.DataFrame(datasets)
df_registry.to_csv(OUT_CSV, index=False)
print(f"✓ Saved registry CSV: {OUT_CSV}")
print(f"  {len(df_registry)} datasets classified\n")

# Classify by status
active = df_registry[df_registry['status'] == 'ACTIVE']
pending = df_registry[df_registry['status'].isin(['PENDING_NORMALIZATION', 'PENDING_ANALYSIS'])]
reference = df_registry[df_registry['status'].isin(['REFERENCE', 'SUPERSEDED'])]

print(f"Classification:")
print(f"  ACTIVE (now): {len(active)} datasets")
for _, row in active.iterrows():
    print(f"    - {row['dataset_name']}: {row['reason']}")

print(f"\n  PENDING (next): {len(pending)} datasets")
for _, row in pending.iterrows():
    print(f"    - {row['dataset_name']}: {row['next_required_action']}")

print(f"\n  REFERENCE (support): {len(reference)} datasets")
for _, row in reference.iterrows():
    print(f"    - {row['dataset_name']}")

# Determine experiment readiness
train_capable = df_registry[df_registry['can_train_soc'] == True]
validate_capable = df_registry[df_registry['can_validate_soc'] == True]
iot_capable = df_registry[df_registry['can_support_iot'] == True]
soh_capable = df_registry[df_registry['can_support_soh'] == True]

# Generate summary MD
with open(OUT_MD, 'w') as f:
    f.write("# Dataset Role Registry\n\n")

    f.write("## Active Datasets (In Use Now)\n\n")
    for _, row in active.iterrows():
        f.write(f"- **{row['dataset_name']}** ({row['scientific_role']})\n")
        f.write(f"  Path: `{row['path']}`\n")
        f.write(f"  Use: {row['primary_use']}\n")
        f.write(f"  Status: {row['status']}\n\n")

    f.write("## Pending Datasets (Next Phase)\n\n")
    for _, row in pending.iterrows():
        f.write(f"- **{row['dataset_name']}**\n")
        f.write(f"  Action: {row['next_required_action']}\n\n")

    f.write("## Support Datasets (Scientific Context)\n\n")
    f.write("- **Literature Baselines:** FNN xEV, BatteryML\n")
    f.write("- **Motivation:** energy-harvesting (IoT), dccpubliclighting (urban)\n\n")

    f.write("## Experiment Readiness\n\n")
    f.write(f"- **SOC validation:** {len(validate_capable)} datasets (Oxford, LG HG2-Discharge, PoliMi-TUB pending)\n")
    f.write(f"- **SOH support:** {len(soh_capable)} datasets (PoliMi-TUB, CALCE SP)\n")
    f.write(f"- **IoT/embedded:** {len(iot_capable)} datasets (CALCE SP, energy-harvesting)\n\n")

    f.write("## Next Technical Steps\n\n")
    f.write("1. **Immediate:** Derive current_abs_A, delta_* in LG; use Discharge subset for eval\n")
    f.write("2. **Short term:** Normalize PoliMi-TUB to Stage 4C schema\n")
    f.write("3. **Parallel:** Extract CALCE SP OCV templates by temperature\n")
    f.write("4. **Context:** Analyze energy-harvesting + dccpubliclighting demand patterns\n")

print(f"\n✓ Saved registry MD: {OUT_MD}")
print(f"\nEXPERIMENT STATUS: Ready for SOC validation (CORE + LG Discharge)")
print(f"NEXT BLOCKER: PoliMi-TUB normalization, CALCE SP OCV extraction")
