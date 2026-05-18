#!/usr/bin/env python3
"""
SP2 Dynamic Profiles Method B Smoke Test - Corrected Version
============================================================
Re-extract and recompute from ZIPs confirmed in root.
No reuse of previous outputs; fresh run only.
"""

import zipfile
import pandas as pd
import numpy as np
from io import BytesIO
from pathlib import Path
import logging

# Setup logging
log_file = Path("/sessions/eager-stoic-euler/mnt/SOC/outputs/external_datasets/sp2_smoke_reconciliation_status.csv")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Paths
ROOT = Path("/sessions/eager-stoic-euler/mnt/SOC")
PDIR = ROOT / "data/processed/external/sp2_dynamic"
PDIR.mkdir(parents=True, exist_ok=True)
ODIR = ROOT / "outputs/external_datasets"
ODIR.mkdir(parents=True, exist_ok=True)

def detect_profile(zip_name):
    """Extract profile type from ZIP name."""
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
    """Extract temperature from ZIP name."""
    if "_0C_" in zip_name:
        return "0C"
    elif "_25C_" in zip_name:
        return "25C"
    elif "_45C_" in zip_name:
        return "45C"
    else:
        return "UNKNOWN"

def select_column(columns, keywords):
    """Find first column matching any of the keywords."""
    for kw in keywords:
        for col in columns:
            if kw in str(col).lower():
                return col
    return None

def process_zip(zip_path):
    """Process one SP2 ZIP file."""
    zip_name = zip_path.name
    profile = detect_profile(zip_name)
    temp = detect_temperature(zip_name)

    logger.info("Processing: " + zip_name + " (Profile: " + profile + ", Temp: " + temp + ")")

    # Validate ZIP
    if not zipfile.is_zipfile(zip_path):
        logger.error("  Not a valid ZIP file")
        return None

    results = []

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Find XLS/XLSX files
            xls_files = [f for f in z.namelist() if f.endswith(('.xls', '.xlsx'))]

            if not xls_files:
                logger.error("  No XLS/XLSX files found")
                return None

            logger.info("  Found " + str(len(xls_files)) + " XLS file(s)")

            # Process first XLS file
            for xls_file in xls_files[:1]:
                logger.info("  Reading " + xls_file + "...")
                file_content = z.read(xls_file)

                try:
                    xls_reader = pd.ExcelFile(BytesIO(file_content))
                    sheet_names = xls_reader.sheet_names
                    logger.info("    Sheets: " + str(sheet_names))

                    # Find Channel sheets
                    channel_sheets = [s for s in sheet_names if 'channel' in s.lower()]

                    if not channel_sheets:
                        logger.warning("    No Channel sheets found")
                        continue

                    # Process each channel sheet
                    for sheet_name in channel_sheets[:1]:  # First channel sheet
                        logger.info("    Sheet: " + sheet_name)

                        try:
                            df = pd.read_excel(
                                BytesIO(file_content),
                                sheet_name=sheet_name,
                                nrows=5000
                            )
                            logger.info("      Shape: " + str(df.shape))
                            logger.info("      Columns: " + str(list(df.columns)[:8]) + "...")

                            # Detect columns
                            time_col = select_column(df.columns, ['time', 'sec'])
                            volt_col = select_column(df.columns, ['voltage', 'volt', 'v('])
                            curr_col = select_column(df.columns, ['current', 'amp', 'a('])
                            temp_col = select_column(df.columns, ['temp', 'celsius', 'c('])

                            if not time_col or not volt_col or not curr_col:
                                logger.warning("      Missing required columns: time=" + str(time_col) + ", volt=" + str(volt_col) + ", curr=" + str(curr_col))
                                continue

                            logger.info("      Detected: time=" + str(time_col) + ", volt=" + str(volt_col) + ", curr=" + str(curr_col) + ", temp=" + str(temp_col))

                            # Extract columns
                            cols_to_keep = [time_col, volt_col, curr_col]
                            if temp_col:
                                cols_to_keep.append(temp_col)

                            df_sel = df[cols_to_keep].copy()
                            df_sel.columns = ['time_s', 'voltage_V', 'current_mA'] + (['temperature_C'] if temp_col else [])

                            # Convert types
                            df_sel['time_s'] = pd.to_numeric(df_sel['time_s'].astype(str), errors='coerce')
                            df_sel['voltage_V'] = pd.to_numeric(df_sel['voltage_V'], errors='coerce')
                            df_sel['current_mA'] = pd.to_numeric(df_sel['current_mA'], errors='coerce')

                            # Normalize voltage (assume mV if > 100)
                            if df_sel['voltage_V'].max() > 100:
                                df_sel['voltage_V'] = df_sel['voltage_V'] / 1000.0

                            # Convert current to Amperes
                            df_sel['current_A'] = df_sel['current_mA'] / 1000.0
                            df_sel['current_abs_A'] = df_sel['current_A'].abs()

                            # Handle temperature
                            if 'temperature_C' not in df_sel.columns:
                                df_sel['temperature_C'] = float(temp.rstrip('C'))  # Use ZIP temperature
                            else:
                                df_sel['temperature_C'] = pd.to_numeric(df_sel['temperature_C'], errors='coerce')

                            # Drop NaN in required columns
                            df_sel = df_sel.dropna(subset=['time_s', 'voltage_V', 'current_A'])

                            if len(df_sel) < 10:
                                logger.warning("      Too few valid rows: " + str(len(df_sel)))
                                continue

                            logger.info("      Valid rows: " + str(len(df_sel)))

                            # Compute deltas
                            df_sel['delta_voltage'] = df_sel['voltage_V'].diff().fillna(0)
                            df_sel['delta_temperature'] = df_sel['temperature_C'].diff().fillna(0)
                            df_sel['delta_current'] = df_sel['current_A'].diff().fillna(0)

                            # Compute Method B coulombic SOC
                            dt = df_sel['time_s'].diff().fillna(0) / 3600.0  # Convert to hours
                            df_sel['q_Ah'] = (df_sel['current_abs_A'] * dt).cumsum()

                            Q_window = df_sel['q_Ah'].max()

                            # Validation
                            has_time = 'time_s' in df_sel.columns
                            has_voltage = 'voltage_V' in df_sel.columns
                            has_current = 'current_A' in df_sel.columns
                            has_temperature = 'temperature_C' in df_sel.columns

                            # Check time monotonicity
                            time_diffs = df_sel['time_s'].diff()
                            time_monotonic = (time_diffs[1:] >= 0).all() or (time_diffs[1:] <= 0).all()

                            # Validation criteria
                            valid = (
                                has_time and has_voltage and has_current and
                                time_monotonic and
                                Q_window >= 0.01 and
                                df_sel['current_abs_A'].std() > 0.001
                            )

                            issues = []
                            if not has_time:
                                issues.append("no_time")
                            if not has_voltage:
                                issues.append("no_voltage")
                            if not has_current:
                                issues.append("no_current")
                            if not time_monotonic:
                                issues.append("time_not_monotonic")
                            if Q_window < 0.01:
                                issues.append(f"Q_window_low({Q_window:.4f})")
                            if df_sel['current_abs_A'].std() <= 0.001:
                                issues.append("current_no_variation")

                            if valid:
                                df_sel['soc_method_b_sp'] = np.clip(1.0 - df_sel['q_Ah'] / Q_window, 0, 1)
                            else:
                                df_sel['soc_method_b_sp'] = np.nan

                            # Add metadata
                            df_sel['dataset'] = 'SP2_DYNAMIC'
                            df_sel['source_zip'] = zip_name
                            df_sel['profile_type'] = profile
                            df_sel['temperature_condition'] = temp
                            df_sel['sheet'] = sheet_name

                            results.append({
                                'data': df_sel,
                                'qa': {
                                    'source_zip': zip_name,
                                    'profile_type': profile,
                                    'temperature_condition': temp,
                                    'zip_valid': True,
                                    'internal_file': xls_file,
                                    'sheets_read': sheet_name,
                                    'rows_extracted': len(df_sel),
                                    'has_time': has_time,
                                    'has_voltage': has_voltage,
                                    'has_current': has_current,
                                    'has_temperature': has_temperature,
                                    'Q_window_min': round(Q_window, 4),
                                    'Q_window_max': round(Q_window, 4),
                                    'soc_min': round(df_sel['soc_method_b_sp'].min(), 4) if valid else np.nan,
                                    'soc_max': round(df_sel['soc_method_b_sp'].max(), 4) if valid else np.nan,
                                    'valid_method_b': valid,
                                    'issues': '; '.join(issues) if issues else 'NONE'
                                }
                            })

                            logger.info("      SUCCESS: valid_method_b=" + str(valid) + ", Q=" + "{:.4f}".format(Q_window) + " Ah")

                        except Exception as e:
                            logger.error("      Error processing sheet: " + str(e)[:100])
                            continue

                except Exception as e:
                    logger.error("    Error reading XLS: " + str(e)[:100])
                    continue

    except Exception as e:
        logger.error("  ZIP processing error: " + str(e)[:100])
        return None

    return results if results else None

# Main execution
logger.info("=" * 80)
logger.info("SP2 Dynamic Profiles Method B Smoke Test - Corrected Run")
logger.info("=" * 80)

# Find ZIPs in root
zip_files = sorted(list(Path("/sessions/eager-stoic-euler/mnt/SOC").glob("SP2_*_*.zip")))

logger.info("ZIPs found in root: " + str(len(zip_files)))
for zf in zip_files:
    logger.info("  " + zf.name)

# Exclude SP2_Initial_capacity
zip_files = [zf for zf in zip_files if "Initial_capacity" not in zf.name]

logger.info("ZIPs to process (excluding Initial_capacity): " + str(len(zip_files)))

all_data = []
all_qa = []

for zip_path in zip_files:
    result = process_zip(zip_path)
    if result:
        for item in result:
            all_data.append(item['data'])
            all_qa.append(item['qa'])

unique_zips_processed = len(set([q['source_zip'] for q in all_qa]))
total_rows_extracted = sum([q['rows_extracted'] for q in all_qa]) if all_qa else 0
logger.info("\nTotal ZIPs processed: " + str(unique_zips_processed))
logger.info("Total rows extracted: " + str(total_rows_extracted))

# Save outputs
if all_data:
    df_smoke = pd.concat(all_data, ignore_index=True)
    cols_keep = [
        'dataset', 'source_zip', 'profile_type', 'temperature_condition', 'sheet',
        'time_s', 'voltage_V', 'current_A', 'current_abs_A', 'temperature_C',
        'delta_voltage', 'delta_temperature', 'delta_current', 'q_Ah', 'soc_method_b_sp'
    ]
    cols_keep = [c for c in cols_keep if c in df_smoke.columns]
    df_smoke = df_smoke[cols_keep]

    smoke_path = PDIR / "sp2_method_b_smoke.parquet"
    df_smoke.to_parquet(smoke_path)
    logger.info("\nOK: Saved parquet to " + str(smoke_path))
    logger.info("  Shape: " + str(df_smoke.shape))

if all_qa:
    df_qa = pd.DataFrame(all_qa)
    qa_path = ODIR / "sp2_dynamic_method_b_smoke_qa.csv"
    df_qa.to_csv(qa_path, index=False)
    logger.info("OK: Saved QA to " + str(qa_path))
    print("\n" + df_qa.to_string())

    # Summary
    unique_zips = len(set([q['source_zip'] for q in all_qa]))
    valid_count = len([q for q in all_qa if q['valid_method_b']])
    total_rows = sum([q['rows_extracted'] for q in all_qa])

    logger.info("\nSummary:")
    logger.info("  ZIPs processed: " + str(unique_zips))
    logger.info("  Total entries: " + str(len(all_qa)))
    logger.info("  Valid Method B: " + str(valid_count))
    logger.info("  Total rows: " + str(total_rows))

logger.info("\nSmoke test execution complete.")
