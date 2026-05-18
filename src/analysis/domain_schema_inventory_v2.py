"""
Domain Schema Inventory v2 — Corrected paths and expanded aliases
QA-validated to use model-ready/corrected datasets
"""

import os
import pandas as pd

# CORRECTED paths — prioritize model-ready/corrected versions
DOMAIN_FILES = {
    "oxford": "/sessions/vigilant-upbeat-goodall/mnt/SOC/CORE/stage4c_final_results/processed/cell_Cell1_processed.csv",
    "lg": "/sessions/vigilant-upbeat-goodall/mnt/SOC/data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_00000.parquet",
    "sp2": "/sessions/vigilant-upbeat-goodall/mnt/SOC/data/processed/external/sp2_dynamic/sp2_method_b_full_corrected.parquet",  # CORRECTED, not FULL
    "iot": "/sessions/vigilant-upbeat-goodall/mnt/SOC/outputs/external_datasets/iot_method_b_extracted.parquet",
}

# Expanded feature aliases
FEATURE_ALIASES = {
    "voltage": ["voltage_v", "voltage_V", "voltage", "V"],
    "temperature": ["temperature_c", "temperature_C", "temperature", "temp_c", "temp", "T"],
    "current": ["current_ma", "current_mA", "current_A", "current_a", "current_abs_A", "current", "I"],
    "delta_voltage": ["delta_voltage", "d_voltage", "dv", "delta_V"],
    "delta_temperature": ["delta_temperature", "d_temperature", "dt", "delta_T"],
    "delta_current": ["delta_current", "d_current", "di", "delta_I"],
}

# Expanded target Method B aliases
TARGET_ALIASES = [
    "method_B_soc_q_cycle", "method_b_soc_q_cycle",
    "soc_method_b", "soc_method_b_sp",
    "soc_target", "soc_source",
    "soc_q_cycle", "SOC_q_cycle",
    "target_soc", "soc",
    "SOC",
    "q_cycle", "Q_cycle",
    "q_mah", "q_Ah",
    "target", "y",
]


def check_column_presence(df, feature_aliases):
    """Check if any alias of a feature exists in dataframe"""
    for alias in feature_aliases:
        if alias in df.columns:
            return True, alias
    return False, None


def check_dataframe_schema(file_path):
    """Load and analyze a dataframe for required features"""
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=5000)
        elif file_path.endswith('.parquet'):
            df = pd.read_parquet(file_path)
        else:
            return None, None, {}, None, "Unsupported file format"

        rows = len(df)
        cols_count = len(df.columns)

        # Check for required features using expanded aliases
        feature_dict = {}
        found_names = {}
        for feat, aliases in FEATURE_ALIASES.items():
            found, actual_name = check_column_presence(df, aliases)
            feature_dict[f"has_{feat}"] = found
            if found:
                found_names[feat] = actual_name

        # Check for target Method B using expanded aliases
        target_col = None
        for target in TARGET_ALIASES:
            if target in df.columns:
                target_col = target
                break

        missing = [f for f in FEATURE_ALIASES.keys() if not feature_dict.get(f"has_{f}")]
        notes = ""

        if missing:
            notes += f"Missing: {', '.join(missing)}. "
        else:
            notes += f"✅ All 6 features found. "

        if target_col:
            notes += f"Target: {target_col}. "
        else:
            notes += "⚠️ Target Method B not found. "

        if found_names:
            notes += f"Aliases: {found_names}. "

        return rows, cols_count, feature_dict, target_col, notes

    except Exception as e:
        return None, None, {}, None, f"Error: {str(e)[:100]}"


def main():
    output_dir = "/sessions/vigilant-upbeat-goodall/mnt/SOC/outputs/domain_adaptation"
    os.makedirs(output_dir, exist_ok=True)

    inventory_data = []

    for domain, file_path in DOMAIN_FILES.items():
        print(f"\n[AUDIT v2] {domain.upper()}: {file_path}")

        if not os.path.exists(file_path):
            print(f"  ❌ File not found")
            inventory_data.append({
                "domain": domain,
                "file_path": file_path,
                "exists": False,
                "rows": None,
                "columns_count": None,
                "has_voltage": False,
                "has_temperature": False,
                "has_current": False,
                "has_delta_voltage": False,
                "has_delta_temperature": False,
                "has_delta_current": False,
                "has_method_b_target": False,
                "target_column": None,
                "missing_required_features": "ALL",
                "notes": "File not found",
            })
            continue

        rows, cols_count, feature_dict, target_col, notes = check_dataframe_schema(file_path)

        if rows is None:
            print(f"  ❌ Could not read: {notes}")
            inventory_data.append({
                "domain": domain,
                "file_path": file_path,
                "exists": True,
                "rows": None,
                "columns_count": None,
                "has_voltage": False,
                "has_temperature": False,
                "has_current": False,
                "has_delta_voltage": False,
                "has_delta_temperature": False,
                "has_delta_current": False,
                "has_method_b_target": False,
                "target_column": None,
                "missing_required_features": "ALL",
                "notes": notes,
            })
            continue

        missing = [f for f in FEATURE_ALIASES.keys() if not feature_dict.get(f"has_{f}")]
        status = "✅ OK" if not missing and target_col else "⚠️ PARTIAL"

        print(f"  {status} {rows:,} rows, {cols_count} cols, target: {target_col}")
        if missing:
            print(f"     Missing: {', '.join(missing)}")

        inventory_data.append({
            "domain": domain,
            "file_path": file_path,
            "exists": True,
            "rows": rows,
            "columns_count": cols_count,
            "has_voltage": feature_dict.get("has_voltage", False),
            "has_temperature": feature_dict.get("has_temperature", False),
            "has_current": feature_dict.get("has_current", False),
            "has_delta_voltage": feature_dict.get("has_delta_voltage", False),
            "has_delta_temperature": feature_dict.get("has_delta_temperature", False),
            "has_delta_current": feature_dict.get("has_delta_current", False),
            "has_method_b_target": target_col is not None,
            "target_column": target_col,
            "missing_required_features": ", ".join(missing) if missing else "NONE",
            "notes": notes,
        })

    # Save CSV
    df_inventory = pd.DataFrame(inventory_data)
    output_file = os.path.join(output_dir, "domain_schema_inventory_v2.csv")
    df_inventory.to_csv(output_file, index=False)

    print(f"\n✅ Inventory v2 saved: {output_file}\n")
    print(df_inventory[["domain", "rows", "columns_count", "missing_required_features", "target_column"]].to_string(index=False))
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
