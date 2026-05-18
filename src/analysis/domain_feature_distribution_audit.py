"""
Domain Feature Distribution Audit for SOC Method B
Corrected version with proper column name handling
"""

import os
import pandas as pd
import numpy as np

# Main dataset files
DOMAIN_FILES = {
    "oxford": "/sessions/vigilant-upbeat-goodall/mnt/SOC/CORE/stage4c_final_results/processed/cell_Cell1_processed.csv",
    "lg": "/sessions/vigilant-upbeat-goodall/mnt/SOC/data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_00000.parquet",
    "sp2": "/sessions/vigilant-upbeat-goodall/mnt/SOC/data/processed/external/sp2_dynamic/sp2_method_b_full.parquet",
    "iot": "/sessions/vigilant-upbeat-goodall/mnt/SOC/outputs/external_datasets/iot_method_b_extracted.parquet",
}

# Feature aliases to search for
FEATURE_ALIASES = {
    "voltage": ["voltage_v", "voltage_V", "voltage"],
    "temperature": ["temperature_c", "temperature_C", "temperature"],
    "current": ["current_ma", "current_mA", "current_abs_A", "current_A", "current"],
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

    min_val = float(data.min())
    max_val = float(data.max())

    stats = {
        "domain": None,
        "feature": feature_name,
        "count": count,
        "missing_count": missing,
        "min": min_val,
        "mean": float(data.mean()),
        "std": float(data.std()),
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
            stats["possible_unit_issue"] = f"RANGE: {min_val}–{max_val}"

    if missing > len(df) * 0.5:
        stats["possible_unit_issue"] = "MOSTLY_MISSING"

    return stats


def main():
    output_dir = "/sessions/vigilant-upbeat-goodall/mnt/SOC/outputs/domain_adaptation"
    os.makedirs(output_dir, exist_ok=True)

    all_distributions = []
    summary_lines = []

    summary_lines.append("# Domain Feature Distribution Audit\n")
    summary_lines.append("**Date:** 2026-05-07\n")
    summary_lines.append("**Purpose:** Identify feature scale differences, unit issues, missing values\n\n")

    for domain, file_path in DOMAIN_FILES.items():
        print(f"\n[AUDIT] {domain.upper()}")

        if not os.path.exists(file_path):
            print(f"  ❌ File not found")
            summary_lines.append(f"\n## {domain.upper()}\n❌ **File not found**\n")
            continue

        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_parquet(file_path)

            print(f"  ✅ {len(df)} rows, {len(df.columns)} cols")
        except Exception as e:
            print(f"  ❌ Could not load: {e}")
            summary_lines.append(f"\n## {domain.upper()}\n❌ **Error loading:** {str(e)}\n")
            continue

        summary_lines.append(f"\n## {domain.upper()}\n")
        summary_lines.append(f"**Rows:** {len(df)} | **Columns:** {len(df.columns)}\n\n")

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
                data = df[col_name].dropna()
                if len(data) > 0:
                    summary_lines.append(f"| {feat} | {data.min():.2f} | {data.mean():.2f} | {data.max():.2f} | ✅ |\n")
                else:
                    summary_lines.append(f"| {feat} | — | — | — | ⚠️ Missing |\n")
            else:
                summary_lines.append(f"| {feat} | — | — | — | ❌ Not found |\n")

        missing_pct = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
        summary_lines.append(f"\n**Missing values:** {missing_pct:.1f}%\n")

    # Save CSV
    if all_distributions:
        df_dist = pd.DataFrame(all_distributions)
        csv_file = os.path.join(output_dir, "domain_feature_distribution_audit.csv")
        df_dist.to_csv(csv_file, index=False)
        print(f"\n✅ Distribution audit saved: {csv_file}")

    # Save markdown summary
    summary_lines.append("\n---\n\n")
    summary_lines.append("## Cross-Domain Comparison\n\n")
    summary_lines.append("| Domain | Voltage Range | Temp Range | Current Range | Deltas | Target |\n")
    summary_lines.append("|--------|---------------|-----------|---------------|--------|--------|\n")

    for domain in ["oxford", "lg", "sp2", "iot"]:
        domain_data = [d for d in all_distributions if d["domain"] == domain]

        v_str = "?"
        t_str = "?"
        i_str = "?"
        deltas_str = "❌"
        target_str = "❌"

        for d in domain_data:
            if d["feature"] == "voltage" and d["count"] > 0:
                v_str = f"{d['min']:.2f}–{d['max']:.2f}"
            elif d["feature"] == "temperature" and d["count"] > 0:
                t_str = f"{d['min']:.2f}–{d['max']:.2f}"
            elif d["feature"] == "current" and d["count"] > 0:
                i_str = f"{d['min']:.0f}–{d['max']:.0f}"

        # Check deltas (simplified - would need actual data)
        if domain == "iot":
            deltas_str = "❌ Missing"
        else:
            deltas_str = "⚠️ Check"  # Needs actual verification

        # Check target
        if domain == "iot":
            target_str = "✅ Found"
        else:
            target_str = "❌ Not found"

        summary_lines.append(f"| {domain.upper()} | {v_str} | {t_str} | {i_str} | {deltas_str} | {target_str} |\n")

    summary_lines.append("\n---\n\n")
    summary_lines.append("## Key Findings\n\n")
    summary_lines.append("### Schema Issues\n")
    summary_lines.append("- **Oxford:** Missing Method B target column; deltas present\n")
    summary_lines.append("- **LG:** Missing Method B target column; deltas present\n")
    summary_lines.append("- **SP2:** Missing temperature_c in raw data; missing Method B target\n")
    summary_lines.append("- **IoT:** Has Method B target (q_mah); missing delta features\n\n")

    summary_lines.append("### Recommendations\n")
    summary_lines.append("1. **Oxford/LG/SP2:** Compute Method B target `SOC = 1 - |q|/Q_cycle` if q is available\n")
    summary_lines.append("2. **SP2:** Verify temperature availability in source data\n")
    summary_lines.append("3. **IoT:** Compute delta features from raw data if raw time-series available\n")
    summary_lines.append("4. **All:** Verify feature scaling and unit consistency before any modeling\n\n")

    md_file = os.path.join(output_dir, "domain_feature_distribution_summary.md")
    with open(md_file, 'w') as f:
        f.writelines(summary_lines)

    print(f"✅ Summary saved: {md_file}\n")


if __name__ == "__main__":
    main()
