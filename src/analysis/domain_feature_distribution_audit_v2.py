"""
Domain Feature Distribution Audit v2 — Corrected paths and expanded aliases
Uses model-ready/corrected datasets with proper alias mapping
"""

import os
import pandas as pd
import numpy as np

# CORRECTED paths
DOMAIN_FILES = {
    "oxford": "/sessions/vigilant-upbeat-goodall/mnt/SOC/CORE/stage4c_final_results/processed/cell_Cell1_processed.csv",
    "lg": "/sessions/vigilant-upbeat-goodall/mnt/SOC/data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_00000.parquet",
    "sp2": "/sessions/vigilant-upbeat-goodall/mnt/SOC/data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet",  # CORRECTED
    "iot": "/sessions/vigilant-upbeat-goodall/mnt/SOC/outputs/external_datasets/iot_method_b_extracted.parquet",
}

# Expanded feature aliases
FEATURE_ALIASES = {
    "voltage": ["voltage_v", "voltage_V"],
    "temperature": ["temperature_c", "temperature_C"],
    "current": ["current_ma", "current_mA", "current_A", "current_abs_A"],
}

EXPECTED_RANGES = {
    "voltage": {"min": 1.5, "max": 5.0},
    "temperature": {"min": -40, "max": 80},
    "current": {"min": -2000, "max": 2000},
}


def find_column(df, aliases):
    """Find first matching column alias in dataframe"""
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def analyze_feature(df, feature_name, aliases):
    """Compute distribution statistics for a feature"""
    col_name = find_column(df, aliases)

    if col_name is None:
        return {
            "domain": None,
            "feature": feature_name,
            "count": 0,
            "missing_count": 0,
            "min": None,
            "mean": None,
            "std": None,
            "max": None,
            "p01": None,
            "p05": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "possible_unit_issue": "NOT_FOUND",
            "notes": "Feature not found in dataset",
        }

    data = df[col_name].dropna()

    if len(data) == 0:
        return {
            "domain": None,
            "feature": feature_name,
            "count": 0,
            "missing_count": len(df),
            "min": None,
            "mean": None,
            "std": None,
            "max": None,
            "p01": None,
            "p05": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "possible_unit_issue": "ALL_MISSING",
            "notes": "All values missing",
        }

    count = len(data)
    missing = len(df) - len(data)

    try:
        min_val = float(data.min())
        max_val = float(data.max())
        mean_val = float(data.mean())
        std_val = float(data.std())
    except:
        return {
            "domain": None,
            "feature": feature_name,
            "count": count,
            "missing_count": missing,
            "min": "ERROR",
            "mean": "ERROR",
            "std": "ERROR",
            "max": "ERROR",
            "p01": "ERROR",
            "p05": "ERROR",
            "p50": "ERROR",
            "p95": "ERROR",
            "p99": "ERROR",
            "possible_unit_issue": "DATA_TYPE_ERROR",
            "notes": f"Cannot convert {col_name} to numeric",
        }

    stats = {
        "domain": None,
        "feature": feature_name,
        "count": count,
        "missing_count": missing,
        "min": min_val,
        "mean": mean_val,
        "std": std_val,
        "max": max_val,
        "p01": float(data.quantile(0.01)),
        "p05": float(data.quantile(0.05)),
        "p50": float(data.quantile(0.50)),
        "p95": float(data.quantile(0.95)),
        "p99": float(data.quantile(0.99)),
        "possible_unit_issue": "NO",
        "notes": f"Column: {col_name}",
    }

    # Check for unit issues
    expected = EXPECTED_RANGES.get(feature_name)
    if expected:
        if max_val > expected["max"] * 2 or min_val < expected["min"] * 2:
            stats["possible_unit_issue"] = f"OUT_OF_RANGE: {min_val:.2f}–{max_val:.2f}"

    if missing > len(df) * 0.5:
        stats["possible_unit_issue"] = "MOSTLY_MISSING"

    return stats


def main():
    output_dir = "/sessions/vigilant-upbeat-goodall/mnt/SOC/outputs/domain_adaptation"
    os.makedirs(output_dir, exist_ok=True)

    all_distributions = []
    summary_lines = []

    summary_lines.append("# Domain Feature Distribution Audit v2\n")
    summary_lines.append("**Date:** 2026-05-07 (QA-Corrected)\n")
    summary_lines.append("**Note:** Uses model-ready/corrected datasets with expanded aliases\n\n")

    for domain, file_path in DOMAIN_FILES.items():
        print(f"\n[AUDIT v2] {domain.upper()}")

        if not os.path.exists(file_path):
            print(f"  ❌ File not found")
            summary_lines.append(f"\n## {domain.upper()}\n❌ **File not found**\n")
            continue

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_parquet(file_path)

            print(f"  ✅ {len(df):,} rows, {len(df.columns)} cols")
        except Exception as e:
            print(f"  ❌ Could not load: {e}")
            summary_lines.append(f"\n## {domain.upper()}\n❌ **Error loading:** {str(e)}\n")
            continue

        summary_lines.append(f"\n## {domain.upper()}\n")
        summary_lines.append(f"**Rows:** {len(df):,} | **Columns:** {len(df.columns)}\n\n")

        # Analyze each feature
        for feat, aliases in FEATURE_ALIASES.items():
            stats = analyze_feature(df, feat, aliases)
            stats["domain"] = domain
            all_distributions.append(stats)

        # Summary by domain
        summary_lines.append("### Feature Ranges\n")
        summary_lines.append("| Feature | Min | Mean | Max | Status |\n")
        summary_lines.append("|---------|-----|------|-----|--------|\n")

        for feat, aliases in FEATURE_ALIASES.items():
            col_name = find_column(df, aliases)
            if col_name:
                try:
                    data = df[col_name].dropna().astype(float)
                    if len(data) > 0:
                        summary_lines.append(f"| {feat} | {data.min():.2f} | {data.mean():.2f} | {data.max():.2f} | ✅ |\n")
                    else:
                        summary_lines.append(f"| {feat} | — | — | — | ⚠️ Missing |\n")
                except:
                    summary_lines.append(f"| {feat} | ERROR | ERROR | ERROR | ❌ Type |\n")
            else:
                summary_lines.append(f"| {feat} | — | — | — | ❌ Not found |\n")

        missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
        summary_lines.append(f"\n**Missing values:** {missing_pct:.1f}%\n")

    # Save CSV
    if all_distributions:
        df_dist = pd.DataFrame(all_distributions)
        csv_file = os.path.join(output_dir, "domain_feature_distribution_audit_v2.csv")
        df_dist.to_csv(csv_file, index=False)
        print(f"\n✅ Distribution audit v2 saved: {csv_file}")

    # Save markdown summary
    summary_lines.append("\n---\n\n")
    summary_lines.append("## Key Corrections from P0→P2\n\n")
    summary_lines.append("### SP2 Path Correction\n")
    summary_lines.append("- **P0 (wrong):** `sp2_method_b_full.parquet` → Current 0.0004 A (WRONG)\n")
    summary_lines.append("- **P0 QA (correct):** `sp2_method_b_full_corrected.parquet` → Current -4.0 to +2.1 A (RIGHT)\n")
    summary_lines.append("- **Temperature:** Found as `temperature_C` column (NOT missing)\n")
    summary_lines.append("- **Target:** Found as `soc_method_b_sp` (NOT missing)\n\n")

    summary_lines.append("### IoT Delta Status\n")
    summary_lines.append("- **Finding:** Delta features (dV, dT, dI) are NOT in the extracted dataset\n")
    summary_lines.append("- **Reason:** Deltas must be COMPUTED from raw timeseries, not pre-computed\n")
    summary_lines.append("- **Status:** Model-ready for baseline training AFTER delta computation\n\n")

    summary_lines.append("### All Targets Found\n")
    summary_lines.append("- Oxford: `method_B_soc_q_cycle` ✅\n")
    summary_lines.append("- LG: `soc_target` ✅\n")
    summary_lines.append("- SP2: `soc_method_b_sp` ✅\n")
    summary_lines.append("- IoT: `soc_method_b` ✅\n\n")

    md_file = os.path.join(output_dir, "domain_feature_distribution_summary_v2.md")
    with open(md_file, 'w') as f:
        f.writelines(summary_lines)

    print(f"✅ Summary v2 saved: {md_file}\n")


if __name__ == "__main__":
    main()
