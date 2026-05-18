"""
Domain Schema Inventory for SOC Method B Multidomain Project
Corrected version with proper domain-specific paths
"""

import os
import pandas as pd

# Define MAIN domain dataset files (actual locations)
DOMAIN_FILES = {
    "oxford": "/sessions/vigilant-upbeat-goodall/mnt/SOC/CORE/stage4c_final_results/processed/cell_Cell1_processed.csv",
    "lg": "/sessions/vigilant-upbeat-goodall/mnt/SOC/data/processed/external/lg18650_hg2/eval_subsets_method_b/clean_all_valid.parquet/part_00000.parquet",
    "sp2": "/sessions/vigilant-upbeat-goodall/mnt/SOC/data/processed/external/sp2_dynamic/sp2_method_b_full.parquet",
    "iot": "/sessions/vigilant-upbeat-goodall/mnt/SOC/outputs/external_datasets/iot_method_b_extracted.parquet",
}

# Required Method B features (with possible column name aliases)
FEATURE_ALIASES = {
    "voltage_v": ["voltage_v", "voltage_V"],
    "temperature_c": ["temperature_c", "temperature_C"],
    "current_ma": ["current_ma", "current_mA", "current_abs_A", "current_A"],
    "delta_voltage": ["delta_voltage", "dv", "delta_V"],
    "delta_temperature": ["delta_temperature", "dt", "delta_T", "delta_C"],
    "delta_current": ["delta_current", "di", "delta_I"],
}

TARGET_ALIASES = [
    "soc", "soc_method_b", "target", "q", "q_mah", "q_mAh",
    "remaining_charge", "coulomb_counter", "state_of_charge"
]


def check_column_presence(df, feature_name, aliases):
    """Check if any alias of a feature exists in dataframe"""
    for alias in aliases:
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

        # Check for required features using aliases
        feature_dict = {}
        found_names = {}
        for feat, aliases in FEATURE_ALIASES.items():
            found, actual_name = check_column_presence(df, feat, aliases)
            feature_dict[f"has_{feat}"] = found
            if found:
                found_names[feat] = actual_name

        # Check for target
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
            notes += f"✅ All features found. "

        if target_col:
            notes += f"Target: {target_col}. "
        else:
            notes += "No Method B target found. "

        if found_names:
            notes += f"Aliases used: {found_names}. "

        return rows, cols_count, feature_dict, target_col, notes

    except Exception as e:
        return None, None, {}, None, f"Error: {str(e)[:100]}"


def main():
    output_dir = "/sessions/vigilant-upbeat-goodall/mnt/SOC/outputs/domain_adaptation"
    os.makedirs(output_dir, exist_ok=True)

    inventory_data = []

    for domain, file_path in DOMAIN_FILES.items():
        print(f"\n[AUDIT] {domain.upper()}: {file_path}")

        if not os.path.exists(file_path):
            print(f"  ❌ File not found")
            inventory_data.append({
                "domain": domain,
                "file_path": file_path,
                "exists": False,
                "rows": None,
                "columns_count": None,
                "has_voltage_v": False,
                "has_temperature_c": False,
                "has_current_ma": False,
                "has_delta_voltage": False,
                "has_delta_temperature": False,
                "has_delta_current": False,
                "has_method_b_target": False,
                "target_column_candidates": None,
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
                "has_voltage_v": False,
                "has_temperature_c": False,
                "has_current_ma": False,
                "has_delta_voltage": False,
                "has_delta_temperature": False,
                "has_delta_current": False,
                "has_method_b_target": False,
                "target_column_candidates": None,
                "missing_required_features": "ALL",
                "notes": notes,
            })
            continue

        missing = [f for f in FEATURE_ALIASES.keys() if not feature_dict.get(f"has_{f}")]
        status = "✅ OK" if not missing and target_col else "⚠️  PARTIAL"

        print(f"  {status} {rows} rows, {cols_count} cols")
        if missing:
            print(f"     Missing: {', '.join(missing)}")
        if target_col:
            print(f"     Target: {target_col}")
        else:
            print(f"     ⚠️  No Method B target found")

        inventory_data.append({
            "domain": domain,
            "file_path": file_path,
            "exists": True,
            "rows": rows,
            "columns_count": cols_count,
            "has_voltage_v": feature_dict.get("has_voltage_v", False),
            "has_temperature_c": feature_dict.get("has_temperature_c", False),
            "has_current_ma": feature_dict.get("has_current_ma", False),
            "has_delta_voltage": feature_dict.get("has_delta_voltage", False),
            "has_delta_temperature": feature_dict.get("has_delta_temperature", False),
            "has_delta_current": feature_dict.get("has_delta_current", False),
            "has_method_b_target": target_col is not None,
            "target_column_candidates": target_col,
            "missing_required_features": ", ".join(missing) if missing else "NONE",
            "notes": notes,
        })

    # Save CSV
    df_inventory = pd.DataFrame(inventory_data)
    output_file = os.path.join(output_dir, "domain_schema_inventory.csv")
    df_inventory.to_csv(output_file, index=False)

    print(f"\n✅ Inventory saved to: {output_file}\n")
    print(df_inventory[["domain", "rows", "columns_count", "missing_required_features", "has_method_b_target"]].to_string(index=False))
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
