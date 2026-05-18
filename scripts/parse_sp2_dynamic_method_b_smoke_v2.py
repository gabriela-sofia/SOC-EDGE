#!/usr/bin/env python3
"""
SP2 Dynamic Profiles Method B Smoke Test (Version 2)
======================================================
Extract samples from SP2 ZIPs, validate schema, compute Method B coulombic SOC.
"""

import zipfile
import pandas as pd
import numpy as np
from io import BytesIO
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Paths
ROOT = Path("/sessions/eager-stoic-euler/mnt/SOC")
PROCESSED_DIR = ROOT / "data/processed/external/sp2_dynamic"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = ROOT / "outputs/external_datasets"

# SP2 ZIPs to process
SP2_ZIPS = [
    "SP2_0C_BJDST.zip",
    "SP2_25C_BJDST.zip",
    "SP2_45C_BJDST.zip",
    "SP2_0C_DST.zip",
    "SP2_25C_DST.zip",
    "SP2_45C_DST.zip",
    "SP2_0C_FUDS.zip",
    "SP2_25C_FUDS.zip",
    "SP2_45C_FUDS.zip",
    "SP2_0C_US06.zip",
    "SP2_25C_US06.zip",
    "SP2_45C_US06.zip",
]

def detect_profile_type(zip_name):
    if "BJDST" in zip_name:
        return "BJDST_DYNAMIC"
    elif "DST" in zip_name:
        return "DST_DYNAMIC"
    elif "FUDS" in zip_name:
        return "FUDS_DYNAMIC"
    elif "US06" in zip_name:
        return "US06_DYNAMIC"
    else:
        return "UNKNOWN"

def detect_temperature(zip_name):
    if "_0C_" in zip_name:
        return "0C"
    elif "_25C_" in zip_name:
        return "25C"
    elif "_45C_" in zip_name:
        return "45C"
    else:
        return "UNKNOWN"

def normalize_column_name(col):
    col_lower = str(col).lower()
    if any(x in col_lower for x in ['time', 'sec', 'second']):
        return 'time_s'
    if any(x in col_lower for x in ['voltage', 'volt', 'v(', 'mv', 'v)']):
        return 'voltage_V'
    if any(x in col_lower for x in ['current', 'amp', 'a(', 'a)', 'ma']):
        return 'current_mA'
    if any(x in col_lower for x in ['temp', 'celsius', 'c(', 'c)']):
        return 'temperature_C'
    return None

def read_xls_smart(zip_path, file_name, nrows=5000):
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            file_content = z.read(file_name)
        xls = pd.ExcelFile(BytesIO(file_content))
        sheets = xls.sheet_names
        channel_sheets = [s for s in sheets if 'channel' in s.lower() or 'channel_1' in s.lower()]
        if not channel_sheets and len(sheets) > 1:
            channel_sheets = [sheets[1]]
        elif not channel_sheets:
            channel_sheets = [sheets[0]]
        results = []
        for sheet in channel_sheets:
            try:
                df = pd.read_excel(BytesIO(file_content), sheet_name=sheet, nrows=nrows)
                results.append((sheet, df))
            except:
                pass
        return results
    except:
        return []

def process_sp2_zip(zip_path):
    zip_name = zip_path.name
    profile_type = detect_profile_type(zip_name)
    temp_cond = detect_temperature(zip_name)
    print("Processing: " + zip_name)

    with zipfile.ZipFile(zip_path, 'r') as z:
        xls_files = [f for f in z.namelist() if f.endswith(('.xls', '.xlsx'))]
    if not xls_files:
        return None

    all_results = []
    for xls_file in xls_files[:1]:
        sheets_data = read_xls_smart(zip_path, xls_file, nrows=5000)
        for sheet_name, df in sheets_data:
            col_mapping = {}
            detected_cols = {}
            for col in df.columns:
                norm_name = normalize_column_name(col)
                if norm_name:
                    col_mapping[col] = norm_name
                    detected_cols[norm_name] = col

            required = {'time_s', 'voltage_V', 'current_mA'}
            if not required.issubset(detected_cols.keys()):
                continue

            df_clean = df[list(col_mapping.keys())].rename(columns=col_mapping).copy()

            # Convert time
            try:
                time_col = df_clean['time_s']
                if pd.api.types.is_datetime64_any_dtype(time_col):
                    time_col = pd.Series(time_col.values)
                    t0 = time_col.iloc[0]
                    df_clean['time_s'] = (time_col - t0).dt.total_seconds()
                else:
                    time_numeric = pd.to_numeric(time_col, errors='coerce')
                    if time_numeric.max() > 1e6:
                        time_numeric = time_numeric / 1000.0
                    df_clean['time_s'] = time_numeric
            except:
                continue

            # Convert voltage
            df_clean['voltage_V'] = pd.to_numeric(df_clean['voltage_V'], errors='coerce')
            if df_clean['voltage_V'].max() > 100:
                df_clean['voltage_V'] = df_clean['voltage_V'] / 1000.0

            # Convert current
            df_clean['current_mA'] = pd.to_numeric(df_clean['current_mA'], errors='coerce')
            df_clean['current_A'] = df_clean['current_mA'] / 1000.0
            df_clean['current_abs_A'] = df_clean['current_A'].abs()

            if 'temperature_C' in detected_cols:
                df_clean['temperature_C'] = pd.to_numeric(df_clean['temperature_C'], errors='coerce')
            else:
                df_clean['temperature_C'] = np.nan

            df_clean = df_clean.dropna(subset=['time_s', 'voltage_V', 'current_A'])
            if len(df_clean) < 10:
                continue

            df_clean['delta_voltage'] = df_clean['voltage_V'].diff().fillna(0)
            df_clean['delta_current'] = df_clean['current_A'].diff().fillna(0)
            df_clean['delta_temperature'] = df_clean['temperature_C'].diff().fillna(0) if not df_clean['temperature_C'].isna().all() else 0.0

            dt = df_clean['time_s'].diff().fillna(0) / 3600.0
            df_clean['q_Ah'] = (df_clean['current_abs_A'] * dt).cumsum()

            Q_window = df_clean['q_Ah'].max()
            valid_method_b = True
            issues = []

            if Q_window <= 0:
                valid_method_b = False
                issues.append("Q_window_zero")
            if df_clean['current_abs_A'].std() < 0.001:
                valid_method_b = False
                issues.append("no_variation")

            if valid_method_b:
                df_clean['soc_method_b_sp'] = np.clip(1.0 - df_clean['q_Ah'] / Q_window, 0, 1)
            else:
                df_clean['soc_method_b_sp'] = np.nan

            df_clean['dataset'] = 'SP2_DYNAMIC'
            df_clean['source_zip'] = zip_name
            df_clean['profile_type'] = profile_type
            df_clean['temperature_condition'] = temp_cond
            df_clean['sheet'] = sheet_name

            summary = {
                'source_zip': zip_name,
                'profile_type': profile_type,
                'temperature_condition': temp_cond,
                'sheet': sheet_name,
                'rows_extracted': len(df_clean),
                'has_time': 'time_s' in detected_cols,
                'has_voltage': 'voltage_V' in detected_cols,
                'has_current': 'current_A' in detected_cols or 'current_mA' in detected_cols,
                'has_temperature': 'temperature_C' in detected_cols,
                'Q_window_Ah': round(Q_window, 3),
                'soc_min': round(df_clean['soc_method_b_sp'].min(), 4) if valid_method_b else np.nan,
                'soc_max': round(df_clean['soc_method_b_sp'].max(), 4) if valid_method_b else np.nan,
                'valid_method_b': valid_method_b,
                'issues': '; '.join(issues) if issues else 'NONE'
            }

            all_results.append({'data': df_clean, 'summary': summary})

    return all_results

# Main
print("SP2 Dynamic Profiles Method B Smoke Test")
print("=" * 60)

all_smoke_data = []
all_summaries = []

for zip_name in SP2_ZIPS:
    zip_path = ROOT / zip_name
    if not zip_path.exists():
        continue
    results = process_sp2_zip(zip_path)
    if results:
        for result in results:
            all_smoke_data.append(result['data'])
            all_summaries.append(result['summary'])

if all_smoke_data:
    df_smoke = pd.concat(all_smoke_data, ignore_index=True)
    standard_cols = [
        'dataset', 'source_zip', 'profile_type', 'temperature_condition', 'sheet',
        'time_s', 'voltage_V', 'current_A', 'current_abs_A', 'temperature_C',
        'delta_voltage', 'delta_temperature', 'delta_current',
        'q_Ah', 'soc_method_b_sp'
    ]
    available_cols = [c for c in standard_cols if c in df_smoke.columns]
    df_smoke = df_smoke[available_cols]
    smoke_parquet = PROCESSED_DIR / "sp2_method_b_smoke.parquet"
    df_smoke.to_parquet(smoke_parquet)
    print("OK: Saved smoke data " + str(smoke_parquet))

if all_summaries:
    df_qa = pd.DataFrame(all_summaries)
    qa_csv = OUTPUT_DIR / "sp2_dynamic_method_b_smoke_qa.csv"
    df_qa.to_csv(qa_csv, index=False)
    print("OK: Saved QA " + str(qa_csv))
    print(df_qa.to_string())

print("\nSummary:")
unique_zips = len(set([s['source_zip'] for s in all_summaries]))
print("ZIPs processed: " + str(unique_zips))
print("Total entries: " + str(len(all_summaries)))
valid_list = [s for s in all_summaries if s['valid_method_b']]
print("Valid Method B: " + str(len(valid_list)))
rows_list = [s['rows_extracted'] for s in all_summaries]
rows_total = sum(rows_list)
print("Total rows extracted: " + str(rows_total))
