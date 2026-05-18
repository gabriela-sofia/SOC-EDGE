#!/usr/bin/env python3
import zipfile
import pandas as pd
import numpy as np
from io import BytesIO
from pathlib import Path

ROOT = Path("/sessions/eager-stoic-euler/mnt/SOC")
PROCESSED_DIR = ROOT / "data/processed/external/sp2_dynamic"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = ROOT / "outputs/external_datasets"

SP2_ZIPS = [
    "SP2_0C_BJDST.zip", "SP2_25C_BJDST.zip", "SP2_45C_BJDST.zip",
    "SP2_0C_DST.zip", "SP2_25C_DST.zip", "SP2_45C_DST.zip",
    "SP2_0C_FUDS.zip", "SP2_25C_FUDS.zip", "SP2_45C_FUDS.zip",
    "SP2_0C_US06.zip", "SP2_25C_US06.zip", "SP2_45C_US06.zip",
]

def get_profile_temp(zip_name):
    profile = "BJDST" if "BJDST" in zip_name else ("DST" if "DST" in zip_name else ("FUDS" if "FUDS" in zip_name else "US06"))
    temp = "0C" if "_0C_" in zip_name else ("25C" if "_25C_" in zip_name else "45C")
    return profile, temp

def normalize_col(col):
    col_lower = str(col).lower()
    if 'time' in col_lower or 'sec' in col_lower:
        return 'time_s'
    if 'voltage' in col_lower or 'volt' in col_lower or 'v(' in col_lower:
        return 'voltage_V'
    if 'current' in col_lower or 'a(' in col_lower:
        return 'current_mA'
    if 'temp' in col_lower or 'c(' in col_lower:
        return 'temperature_C'
    return None

all_data = []
all_qa = []

for zip_name in SP2_ZIPS:
    zip_path = ROOT / zip_name
    if not zip_path.exists():
        continue

    profile, temp = get_profile_temp(zip_name)
    print("Processing:", zip_name)

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            xls_files = [f for f in z.namelist() if f.endswith(('.xls', '.xlsx'))]

            for xls_file in xls_files[:1]:
                file_content = z.read(xls_file)
                xls_reader = pd.ExcelFile(BytesIO(file_content))

                for sheet_name in xls_reader.sheet_names:
                    if 'channel' not in sheet_name.lower():
                        continue

                    df = pd.read_excel(BytesIO(file_content), sheet_name=sheet_name, nrows=5000)

                    col_mapping = {}
                    for col in df.columns:
                        norm = normalize_col(col)
                        if norm:
                            col_mapping[col] = norm

                    if not {'time_s', 'voltage_V', 'current_mA'}.issubset(set(col_mapping.values())):
                        continue

                    df = df[list(col_mapping.keys())].rename(columns=col_mapping).copy()

                    df['time_s'] = df['time_s'].astype(str)
                    df['time_s'] = pd.to_numeric(df['time_s'], errors='coerce')
                    df['voltage_V'] = pd.to_numeric(df['voltage_V'], errors='coerce')
                    df['current_mA'] = pd.to_numeric(df['current_mA'], errors='coerce')

                    if df['voltage_V'].max() > 100:
                        df['voltage_V'] = df['voltage_V'] / 1000.0
                    df['current_A'] = df['current_mA'] / 1000.0
                    df['current_abs_A'] = df['current_A'].abs()

                    if 'temperature_C' in df.columns:
                        df['temperature_C'] = pd.to_numeric(df['temperature_C'], errors='coerce')
                    else:
                        df['temperature_C'] = np.nan

                    df = df.dropna(subset=['time_s', 'voltage_V', 'current_A'])
                    if len(df) < 10:
                        continue

                    df['delta_voltage'] = df['voltage_V'].diff().fillna(0)
                    df['delta_current'] = df['current_A'].diff().fillna(0)
                    df['delta_temperature'] = df['temperature_C'].diff().fillna(0) if not df['temperature_C'].isna().all() else 0.0

                    dt = df['time_s'].diff().fillna(0) / 3600.0
                    df['q_Ah'] = (df['current_abs_A'] * dt).cumsum()
                    Q = df['q_Ah'].max()

                    valid = Q > 0 and df['current_abs_A'].std() > 0.001
                    if valid:
                        df['soc_method_b_sp'] = np.clip(1.0 - df['q_Ah'] / Q, 0, 1)
                    else:
                        df['soc_method_b_sp'] = np.nan

                    df['dataset'] = 'SP2_DYNAMIC'
                    df['source_zip'] = zip_name
                    df['profile_type'] = profile
                    df['temperature_condition'] = temp
                    df['sheet'] = sheet_name

                    all_data.append(df)

                    all_qa.append({
                        'source_zip': zip_name,
                        'profile_type': profile,
                        'temperature_condition': temp,
                        'sheet': sheet_name,
                        'rows_extracted': len(df),
                        'has_time': True,
                        'has_voltage': True,
                        'has_current': True,
                        'has_temperature': not df['temperature_C'].isna().all(),
                        'Q_window_Ah': round(Q, 3),
                        'soc_min': round(df['soc_method_b_sp'].min(), 4) if valid else np.nan,
                        'soc_max': round(df['soc_method_b_sp'].max(), 4) if valid else np.nan,
                        'valid_method_b': valid,
                        'issues': 'NONE' if valid else 'Q_invalid or no_variation'
                    })
    except Exception as e:
        print("  ERROR:", str(e)[:60])
        continue

if all_data:
    df_smoke = pd.concat(all_data, ignore_index=True)
    cols_keep = ['dataset', 'source_zip', 'profile_type', 'temperature_condition', 'sheet', 'time_s', 'voltage_V', 'current_A', 'current_abs_A', 'temperature_C', 'delta_voltage', 'delta_temperature', 'delta_current', 'q_Ah', 'soc_method_b_sp']
    cols_keep = [c for c in cols_keep if c in df_smoke.columns]
    df_smoke = df_smoke[cols_keep]

    smoke_path = PROCESSED_DIR / "sp2_method_b_smoke.parquet"
    df_smoke.to_parquet(smoke_path)
    print("\nOK: Saved smoke " + str(smoke_path))

if all_qa:
    df_qa = pd.DataFrame(all_qa)
    qa_path = OUTPUT_DIR / "sp2_dynamic_method_b_smoke_qa.csv"
    df_qa.to_csv(qa_path, index=False)
    print("OK: Saved QA " + str(qa_path))
    print(df_qa.to_string())

print("\nSummary:")
if all_qa:
    unique_zips = len(set([q['source_zip'] for q in all_qa]))
    valid_count = len([q for q in all_qa if q['valid_method_b']])
    total_rows = sum([q['rows_extracted'] for q in all_qa])
    print("ZIPs processed:", unique_zips)
    print("Total entries:", len(all_qa))
    print("Valid Method B:", valid_count)
    print("Total rows extracted:", total_rows)
d Method B:", valid_count)
    print("Total rows extracted:", total_rows)
