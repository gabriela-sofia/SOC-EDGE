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

def norm(col):
    cl = str(col).lower()
    if 'time' in cl or 'sec' in cl: return 'time_s'
    if 'volt' in cl or 'v(' in cl: return 'voltage_V'
    if 'curr' in cl or 'a(' in cl: return 'current_mA'
    if 'temp' in cl or 'c(' in cl: return 'temperature_C'
    return None

ads = []
aqa = []

for zn in ZIPS:
    zp = ROOT / zn
    if not zp.exists(): continue
    p, t = prof_temp(zn)
    print("Processing:", zn)
    try:
        with zipfile.ZipFile(zp) as z:
            xls = [f for f in z.namelist() if f.endswith(('.xls', '.xlsx'))]
            for xf in xls[:1]:
                fc = z.read(xf)
                xls_r = pd.ExcelFile(BytesIO(fc))
                for sn in xls_r.sheet_names:
                    if 'channel' not in sn.lower(): continue
                    df = pd.read_excel(BytesIO(fc), sheet_name=sn, nrows=5000)
                    cm = {}
                    for col in df.columns:
                        n = norm(col)
                        if n: cm[col] = n
                    if not {'time_s', 'voltage_V', 'current_mA'}.issubset(set(cm.values())): continue
                    df = df[list(cm.keys())].rename(columns=cm)
                    df['time_s'] = pd.to_numeric(df['time_s'].astype(str), errors='coerce')
                    df['voltage_V'] = pd.to_numeric(df['voltage_V'], errors='coerce')
                    df['current_mA'] = pd.to_numeric(df['current_mA'], errors='coerce')
                    if df['voltage_V'].max() > 100: df['voltage_V'] /= 1000.0
                    df['current_A'] = df['current_mA'] / 1000.0
                    df['current_abs_A'] = df['current_A'].abs()
                    if 'temperature_C' in df: df['temperature_C'] = pd.to_numeric(df['temperature_C'], errors='coerce')
                    else: df['temperature_C'] = np.nan
                    df = df.dropna(subset=['time_s', 'voltage_V', 'current_A'])
                    if len(df) < 10: continue
                    df['delta_voltage'] = df['voltage_V'].diff().fillna(0)
                    df['delta_current'] = df['current_A'].diff().fillna(0)
                    df['delta_temperature'] = df['temperature_C'].diff().fillna(0)
                    dt = df['time_s'].diff().fillna(0) / 3600.0
                    df['q_Ah'] = (df['current_abs_A'] * dt).cumsum()
                    Q = df['q_Ah'].max()
                    v = Q > 0 and df['current_abs_A'].std() > 0.001
                    if v: df['soc_method_b_sp'] = np.clip(1.0 - df['q_Ah'] / Q, 0, 1)
                    else: df['soc_method_b_sp'] = np.nan
                    df['dataset'] = 'SP2_DYNAMIC'
                    df['source_zip'] = zn
                    df['profile_type'] = p
                    df['temperature_condition'] = t
                    df['sheet'] = sn
                    ads.append(df)
                    aqa.append({'source_zip': zn, 'profile_type': p, 'temperature_condition': t, 'sheet': sn, 'rows_extracted': len(df), 'has_time': True, 'has_voltage': True, 'has_current': True, 'has_temperature': not df['temperature_C'].isna().all(), 'Q_window_Ah': round(Q, 3), 'soc_min': round(df['soc_method_b_sp'].min(), 4) if v else np.nan, 'soc_max': round(df['soc_method_b_sp'].max(), 4) if v else np.nan, 'valid_method_b': v, 'issues': 'NONE' if v else 'Q_invalid'})
    except Exception as e:
        print("  ERROR:", str(e)[:60])

if ads:
    dfs = pd.concat(ads, ignore_index=True)
    cp = ['dataset', 'source_zip', 'profile_type', 'temperature_condition', 'sheet', 'time_s', 'voltage_V', 'current_A', 'current_abs_A', 'temperature_C', 'delta_voltage', 'delta_temperature', 'delta_current', 'q_Ah', 'soc_method_b_sp']
    cp = [c for c in cp if c in dfs.columns]
    dfs = dfs[cp]
    sp = PDIR / "sp2_method_b_smoke.parquet"
    dfs.to_parquet(sp)
    print("\nOK Smoke:", sp)

if aqa:
    dqa = pd.DataFrame(aqa)
    qp = ODIR / "sp2_dynamic_method_b_smoke_qa.csv"
    dqa.to_csv(qp, index=False)
    print("OK QA:", qp)
    print(dqa.to_string())
    print("\nZIPs:", len(set([q['source_zip'] for q in aqa])))
    print("Valid:", len([q for q in aqa if q['valid_method_b']]))
    print("Rows:", sum([q['rows_extracted'] for q in aqa]))
