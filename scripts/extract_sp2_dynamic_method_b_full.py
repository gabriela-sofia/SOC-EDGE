#!/usr/bin/env python3
"""
SP2 Dynamic Profiles Method B Full Extraction
==============================================
No row limit. Full-cycle detection. Per-cycle Q_cycle computation.
"""

import zipfile, pandas as pd, numpy as np
from io import BytesIO
from pathlib import Path

ROOT = Path("/sessions/eager-stoic-euler/mnt/SOC")
PDIR = ROOT / "data/processed/external/sp2_dynamic"
PDIR.mkdir(parents=True, exist_ok=True)
ODIR = ROOT / "outputs/external_datasets"

ZIPS = ["SP2_0C_BJDST.zip", "SP2_25C_BJDST.zip", "SP2_45C_BJDST.zip",
        "SP2_0C_DST.zip", "SP2_25C_DST.zip", "SP2_45C_DST.zip",
        "SP2_0C_FUDS.zip", "SP2_25C_FUDS.zip", "SP2_45C_FUDS.zip",
        "SP2_0C_US06.zip", "SP2_25C_US06.zip", "SP2_45C_US06.zip"]

def prof_temp(zn):
    p = "BJDST" if "BJDST" in zn else ("DST" if "DST" in zn else ("FUDS" if "FUDS" in zn else "US06"))
    t = "0C" if "_0C_" in zn else ("25C" if "_25C_" in zn else "45C")
    return p, t

def select_col(cols, pattern):
    for c in cols:
        if pattern in str(c).lower():
            return c
    return None

def detect_cycles(df_sheet):
    """
    Detect cycle/segment boundaries within a sheet by time restart or large gap.
    Returns list of (cycle_id, start_idx, end_idx) tuples.
    """
    if len(df_sheet) < 1:
        return []

    df = df_sheet.reset_index(drop=True)
    cycles = []
    cycle_id = 0
    start_idx = 0

    time_col = 'time_s'
    if time_col not in df.columns:
        return [(0, 0, len(df))]

    # Detect restarts or large gaps
    for i in range(1, len(df)):
        curr_time = df.loc[i, time_col]
        prev_time = df.loc[i-1, time_col]

        # Restart if time goes backward or very large gap (> 60 seconds)
        if curr_time < prev_time or (curr_time - prev_time) > 60:
            cycles.append((cycle_id, start_idx, i))
            cycle_id += 1
            start_idx = i

    # Final cycle
    cycles.append((cycle_id, start_idx, len(df)))

    return cycles

all_data = []
all_qa = []

print("SP2 Dynamic Method B Full Extraction\n" + "="*60)

for zn in ZIPS:
    zp = ROOT / zn
    if not zp.exists():
        print(f"SKIP: {zn} (not found)")
        continue

    p, t = prof_temp(zn)
    print(f"\nProcessing: {zn} ({p}, {t})")

    try:
        with zipfile.ZipFile(zp) as z:
            xls = [f for f in z.namelist() if f.endswith(('.xls', '.xlsx'))]
            for xf in xls[:1]:
                fc = z.read(xf)
                xls_r = pd.ExcelFile(BytesIO(fc))

                for sn in xls_r.sheet_names:
                    if 'channel' not in sn.lower():
                        continue

                    # Read ALL rows (no limit)
                    df = pd.read_excel(BytesIO(fc), sheet_name=sn)

                    # Column selection
                    tc = select_col(df.columns, 'test_time')
                    vc = select_col(df.columns, 'voltage')
                    cc = select_col(df.columns, 'current')

                    if not tc or not vc or not cc:
                        print(f"  {sn}: Missing required columns")
                        continue

                    df_sel = df[[tc, vc, cc]].copy()
                    df_sel.columns = ['time_s', 'voltage_V', 'current_mA']

                    # Type conversion
                    df_sel['time_s'] = pd.to_numeric(df_sel['time_s'].astype(str), errors='coerce')
                    df_sel['voltage_V'] = pd.to_numeric(df_sel['voltage_V'], errors='coerce')
                    df_sel['current_mA'] = pd.to_numeric(df_sel['current_mA'], errors='coerce')

                    if df_sel['voltage_V'].max() > 100:
                        df_sel['voltage_V'] /= 1000.0

                    df_sel['current_A'] = df_sel['current_mA'] / 1000.0
                    df_sel['current_abs_A'] = df_sel['current_A'].abs()
                    df_sel['temperature_C'] = np.nan

                    df_sel = df_sel.dropna(subset=['time_s', 'voltage_V', 'current_A'])
                    if len(df_sel) < 10:
                        print(f"  {sn}: Too few valid rows ({len(df_sel)})")
                        continue

                    df_sel = df_sel.sort_values('time_s').reset_index(drop=True)

                    # Deltas
                    df_sel['delta_voltage'] = df_sel['voltage_V'].diff().fillna(0)
                    df_sel['delta_current'] = df_sel['current_A'].diff().fillna(0)
                    df_sel['delta_temperature'] = 0.0

                    # Detect cycles
                    cycles = detect_cycles(df_sel)

                    print(f"  {sn}: {len(df_sel)} rows, {len(cycles)} cycle(s)")

                    # Process each cycle
                    for cycle_id, start_idx, end_idx in cycles:
                        df_cyc = df_sel.iloc[start_idx:end_idx].copy()

                        if len(df_cyc) < 10:
                            continue

                        df_cyc['row_index'] = range(len(df_cyc))

                        # Method B computation
                        dt = df_cyc['time_s'].diff().fillna(0) / 3600.0
                        df_cyc['q_Ah'] = (df_cyc['current_abs_A'] * dt).cumsum()
                        Q = df_cyc['q_Ah'].max()

                        v = Q > 0.01 and df_cyc['current_abs_A'].std() > 0.001

                        if v:
                            df_cyc['soc_method_b_sp'] = np.clip(1.0 - df_cyc['q_Ah'] / Q, 0, 1)
                        else:
                            df_cyc['soc_method_b_sp'] = np.nan

                        # Metadata
                        df_cyc['dataset'] = 'SP2_DYNAMIC'
                        df_cyc['source_zip'] = zn
                        df_cyc['profile_type'] = p
                        df_cyc['temperature_condition'] = t
                        df_cyc['sheet'] = sn
                        df_cyc['cycle_id'] = cycle_id

                        all_data.append(df_cyc)

                        # QA per cycle
                        time_diffs = df_cyc['time_s'].diff()
                        time_mono = (time_diffs[1:] >= -0.01).all()  # Allow tiny negatives

                        issues = []
                        if not time_mono:
                            issues.append("time_not_monotonic")
                        if Q < 0.01:
                            issues.append(f"Q_low({Q:.4f})")
                        if df_cyc['current_abs_A'].std() <= 0.001:
                            issues.append("no_variation")

                        all_qa.append({
                            'source_zip': zn,
                            'profile_type': p,
                            'temperature_condition': t,
                            'sheet': sn,
                            'cycle_id': cycle_id,
                            'rows': len(df_cyc),
                            'time_start': round(df_cyc['time_s'].min(), 2),
                            'time_end': round(df_cyc['time_s'].max(), 2),
                            'duration_s': round(df_cyc['time_s'].max() - df_cyc['time_s'].min(), 2),
                            'Q_cycle_Ah': round(Q, 4),
                            'soc_min': round(df_cyc['soc_method_b_sp'].min(), 4) if v else np.nan,
                            'soc_max': round(df_cyc['soc_method_b_sp'].max(), 4) if v else np.nan,
                            'current_mean_A': round(df_cyc['current_A'].mean(), 4),
                            'current_max_A': round(df_cyc['current_abs_A'].max(), 4),
                            'voltage_min': round(df_cyc['voltage_V'].min(), 3),
                            'voltage_max': round(df_cyc['voltage_V'].max(), 3),
                            'valid_method_b': v,
                            'issues': '; '.join(issues) if issues else 'NONE'
                        })

    except Exception as e:
        print(f"  ERROR: {str(e)[:80]}")

# Save outputs
if all_data:
    dfs = pd.concat(all_data, ignore_index=True)
    cp = ['dataset', 'source_zip', 'profile_type', 'temperature_condition', 'sheet', 'cycle_id', 'row_index', 'time_s', 'voltage_V', 'current_A', 'current_abs_A', 'temperature_C', 'delta_voltage', 'delta_temperature', 'delta_current', 'q_Ah', 'soc_method_b_sp']
    cp = [c for c in cp if c in dfs.columns]
    dfs = dfs[cp]

    fp = PDIR / "sp2_method_b_full.parquet"
    dfs.to_parquet(fp)
    print(f"\n[OK] Parquet: {fp} ({dfs.shape})")

if all_qa:
    dqa = pd.DataFrame(all_qa)
    qp = ODIR / "sp2_dynamic_method_b_full_qa.csv"
    dqa.to_csv(qp, index=False)
    print(f"[OK] QA CSV: {qp} ({len(dqa)} rows)")

    # Cycle summary
    cyc_sum = dqa.groupby(['profile_type', 'temperature_condition']).agg({
        'Q_cycle_Ah': ['min', 'mean', 'max'],
        'valid_method_b': 'sum',
        'rows': 'sum'
    }).round(4)

    sp = ODIR / "sp2_dynamic_method_b_cycle_summary.csv"
    cyc_sum.to_csv(sp)
    print(f"[OK] Cycle summary: {sp}")

    # Status summary
    unique_zips = len(set([q['source_zip'] for q in all_qa]))
    total_rows = sum([q['rows'] for q in all_qa])
    valid_count = len([q for q in all_qa if q['valid_method_b']])
    total_cycles = len(all_qa)
    Q_min = min([q['Q_cycle_Ah'] for q in all_qa])
    Q_mean = np.mean([q['Q_cycle_Ah'] for q in all_qa])
    Q_max = max([q['Q_cycle_Ah'] for q in all_qa])

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  ZIPs processed: {unique_zips}/12")
    print(f"  Total rows: {total_rows:,}")
    print(f"  Total cycles/windows: {total_cycles}")
    print(f"  Valid Method B: {valid_count}/{total_cycles}")
    print(f"  Q_cycle range: [{Q_min:.4f}, {Q_mean:.4f}, {Q_max:.4f}] Ah")

    if valid_count == total_cycles:
        decision = "SP2_DYNAMIC_METHOD_B_FULL_READY"
    elif valid_count > 0:
        decision = "SP2_DYNAMIC_METHOD_B_PARTIAL"
    else:
        decision = "SP2_DYNAMIC_METHOD_B_NEEDS_FIX"

    print(f"\nDecision: {decision}")

    # Status CSV
    ss = ODIR / "sp2_dynamic_method_b_full_status.csv"
    pd.DataFrame([{
        'component': 'SP2_Full_Extraction',
        'status': 'COMPLETE',
        'zips_processed': unique_zips,
        'total_rows': total_rows,
        'total_cycles': total_cycles,
        'valid_method_b': valid_count,
        'Q_min': Q_min,
        'Q_mean': Q_mean,
        'Q_max': Q_max,
        'decision': decision
    }]).to_csv(ss, index=False)
    print(f"[OK] Status: {ss}")

print(f"\nFull extraction complete.\n")
