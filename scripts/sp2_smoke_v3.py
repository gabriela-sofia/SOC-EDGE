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

ads, aqa = [], []

for zn in ZIPS:
    zp = ROOT / zn
    if not zp.exists():
        continue
    p, t = prof_temp(zn)
    print("Processing:", zn)
    try:
        with zipfile.ZipFile(zp) as z:
            xls = [f for f in z.namelist() if f.endswith(('.xls', '.xlsx'))]
            for xf in xls[:1]:
                fc = z.read(xf)
                xls_r = pd.ExcelFile(BytesIO(fc))
                for sn in xls_r.sheet_names:
                    if 'channel' not in sn.lower():
                        continue
                    df = pd.read_excel(BytesIO(fc), sheet_name=sn, nrows=5000)

                    # Select specific columns
                    tc = select_col(df.columns, 'test_time')
                    vc = select_col(df.columns, 'voltage')
                    cc = select_col(df.columns, 'current')

                    if not tc or not vc or not cc:
                        continue

                    df_sel = df[[tc, vc, cc]].copy()
                    df_sel.columns = ['time_s', 'voltage_V', 'current_mA']

                    # Convert types
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
                        continue

                    df_sel['delta_voltage'] = df_sel['voltage_V'].diff().fillna(0)
                    df_sel['delta_current'] = df_sel['current_A'].diff().fillna(0)
                    df_sel['delta_temperature'] = 0.0

                    dt = df_sel['time_s'].diff().fillna(0) / 3600.0
                    df_sel['q_Ah'] = (df_sel['current_abs_A'] * dt).cumsum()
                    Q = df_sel['q_Ah'].max()
                    v = Q > 0 and df_sel['current_abs_A'].std() > 0.001

                    if v:
                        df_sel['soc_method_b_sp'] = np.clip(1.0 - df_sel['q_Ah'] / Q, 0, 1)
                    else:
                        df_sel['soc_method_b_sp'] = np.nan

                    df_sel['dataset'] = 'SP2_DYNAMIC'
                    df_sel['source_zip'] = zn
                    df_sel['profile_type'] = p
                    df_sel['temperature_condition'] = t
                    df_sel['sheet'] = sn

                    ads.append(df_sel)

                    aqa.append({
                        'source_zip': zn,
                        'profile_type': p,
                        'temperature_condition': t,
                        'sheet': sn,
                        'rows_extracted': len(df_sel),
                        'has_time': True,
                        'has_voltage': True,
                        'has_current': True,
                        'has_temperature': False,
                        'Q_window_Ah': round(Q, 3),
                        'soc_min': round(df_sel['soc_method_b_sp'].min(), 4) if v else np.nan,
                        'soc_max': round(df_sel['soc_method_b_sp'].max(), 4) if v else np.nan,
                        'valid_method_b': v,
                        'issues': 'NONE' if v else 'Q_invalid'
                    })
    except Exception as e:
        print("  ERROR:", str(e)[:80])

if ads:
    dfs = pd.concat(ads, ignore_index=True)
    cp = ['dataset', 'source_zip', 'profile_type', 'temperature_condition', 'sheet', 'time_s', 'voltage_V', 'current_A', 'current_abs_A', 'temperature_C', 'delta_voltage', 'delta_temperature', 'delta_current', 'q_Ah', 'soc_method_b_sp']
    cp = [c for c in cp if c in dfs.columns]
    dfs = dfs[cp]
    sp = PDIR / "sp2_method_b_smoke.parquet"
    dfs.to_parquet(sp)
    print("\nOK Smoke saved")

if aqa:
    dqa = pd.DataFrame(aqa)
    qp = ODIR / "sp2_dynamic_method_b_smoke_qa.csv"
    dqa.to_csv(qp, index=False)
    print("OK QA saved")
    print(dqa.to_string())
    print("\nZIPs processed:", len(set([q['source_zip'] for q in aqa])))
    print("Valid Method B:", len([q for q in aqa if q['valid_method_b']]))
    print("Total rows:", sum([q['rows_extracted'] for q in aqa]))
