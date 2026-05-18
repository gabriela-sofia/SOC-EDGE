#!/usr/bin/env python3
"""
Normalize all 208 LG18650_HG2 CSVs to parquet (partitioned).
No training, no deletions, schema-final format.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import csv

def time_str_to_seconds(t_str):
    """HH:MM:SS.mmm to seconds."""
    if pd.isna(t_str):
        return np.nan
    try:
        parts = str(t_str).split(':')
        if len(parts) != 3:
            return np.nan
        h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    except:
        return np.nan

PROJECT_ROOT = Path(".")
MANIFEST = "outputs/external_datasets/lg18650_hg2_schema_manifest.csv"
OUT_PARQUET = Path("data/processed/external/lg18650_hg2")
OUT_QA = Path("outputs/external_datasets/lg18650_hg2_full_normalization_qa.csv")
OUT_SUMMARY = Path("outputs/external_datasets/lg18650_hg2_full_normalization_summary.md")

OUT_PARQUET.mkdir(parents=True, exist_ok=True)
Path("outputs/external_datasets").mkdir(parents=True, exist_ok=True)

# Read manifest
manifest_df = pd.read_csv(MANIFEST)

print(f"Normalizing {len(manifest_df)} files...\n")

all_data = []
qa_rows = []
ok_count = 0
error_count = 0

for idx, f_info in manifest_df.iterrows():
    fpath = PROJECT_ROOT / f_info["file_path"]
    fname = Path(f_info["file_path"]).name
    profile = f_info["profile_type"]
    cell = str(f_info["cell_id"])
    temp_cond = f_info["temperature_condition"]

    try:
        # Read
        df = pd.read_csv(fpath, skiprows=28, encoding='utf-8', low_memory=False)
        df = df.iloc[1:].reset_index(drop=True)  # Remove unit row

        # Convert time
        time_s = df['Step Time'].apply(time_str_to_seconds)
        voltage_V = pd.to_numeric(df['Voltage'], errors='coerce')
        current_A = pd.to_numeric(df['Current'], errors='coerce')
        temperature_C = pd.to_numeric(df['Temperature'], errors='coerce')
        capacity_Ah = pd.to_numeric(df.get('Capacity', pd.Series(np.nan)), errors='coerce')

        # Valid rows
        valid = ~(pd.isna(time_s) | pd.isna(voltage_V) | pd.isna(current_A) | pd.isna(temperature_C))

        if valid.sum() < 10:
            error_count += 1
            print(f"  ERR {fname[:40]:40s} <10 valid rows")
            continue

        # Build normalized DF
        dn = pd.DataFrame({
            'dataset': 'lg18650_hg2',
            'cell_id': cell,
            'profile_type': profile,
            'temperature_condition': temp_cond,
            'cycle_id': 1,
            'time_s': time_s[valid].values,
            'voltage_V': voltage_V[valid].values,
            'current_A': current_A[valid].values,
            'temperature_C': temperature_C[valid].values,
            'capacity_Ah': capacity_Ah[valid].values,
        })

        # SOC: Method A (Capacity-based)
        cap_valid = ~pd.isna(dn['capacity_Ah'])
        soc_all = np.full(len(dn), np.nan, dtype=float)
        soc_method = 'capacity'

        if cap_valid.sum() > 0:
            ca = np.abs(dn.loc[cap_valid, 'capacity_Ah'].values)
            cm = np.nanmax(ca)
            if cm > 0:
                soc_all[cap_valid] = 1.0 - ca / cm
            else:
                # Fallback to integral if capacity range is zero
                c = dn['current_A'].values.astype(float)
                t = dn['time_s'].values.astype(float)
                dt = np.diff(t, prepend=0)
                q = np.cumsum(c * dt)
                qa_abs = np.abs(q)
                qm = np.nanmax(qa_abs)
                if qm > 1e-6:
                    soc_all = 1.0 - qa_abs / qm
                    soc_method = 'current_integral'
                else:
                    # Final fallback: nominal
                    soc_all = 1.0 - qa_abs / 2.8
                    soc_method = 'nominal_2p8'
        else:
            # No capacity: use current integral
            c = dn['current_A'].values.astype(float)
            t = dn['time_s'].values.astype(float)
            dt = np.diff(t, prepend=0)
            q = np.cumsum(c * dt)
            qa_abs = np.abs(q)
            qm = np.nanmax(qa_abs)
            if qm > 1e-6:
                soc_all = 1.0 - qa_abs / qm
                soc_method = 'current_integral'
            else:
                soc_all = 1.0 - qa_abs / 2.8
                soc_method = 'nominal_2p8'

        dn['soc_target'] = np.clip(soc_all, 0, 1)
        dn['soc_method'] = soc_method
        dn['source_file'] = fname

        # Determine train_eligible
        # Mark as False if: charge profile with ambiguous SOC (close to 1), or method != capacity
        train_eligible = True
        notes = ""

        if soc_method != 'capacity':
            train_eligible = False
            notes = f"soc_method={soc_method}"
        elif 'charge' in profile.lower():
            # Charge: if SOC mostly >= 0.95, it's ambiguous
            if (dn['soc_target'] >= 0.95).sum() > len(dn) * 0.5:
                train_eligible = False
                notes = "charge_profile_high_soc"

        dn['train_eligible'] = train_eligible
        dn['notes'] = notes

        all_data.append(dn)

        # QA
        qa_rows.append({
            'file_name': fname,
            'profile_type': profile,
            'cell_id': cell,
            'n_rows': len(dn),
            'time_ok': not pd.isna(dn['time_s']).any(),
            'voltage_min': f"{dn['voltage_V'].min():.2f}",
            'voltage_max': f"{dn['voltage_V'].max():.2f}",
            'current_min': f"{dn['current_A'].min():.3f}",
            'current_max': f"{dn['current_A'].max():.3f}",
            'temp_min': f"{dn['temperature_C'].min():.1f}",
            'temp_max': f"{dn['temperature_C'].max():.1f}",
            'capacity_min': f"{dn['capacity_Ah'].min():.3f}" if not pd.isna(dn['capacity_Ah']).all() else "N/A",
            'capacity_max': f"{dn['capacity_Ah'].max():.3f}" if not pd.isna(dn['capacity_Ah']).all() else "N/A",
            'soc_min': f"{dn['soc_target'].min():.3f}",
            'soc_max': f"{dn['soc_target'].max():.3f}",
            'soc_method': soc_method,
            'train_eligible': train_eligible,
            'issue': notes if notes else 'OK'
        })

        ok_count += 1
        if ok_count % 50 == 0:
            print(f"  Processed {ok_count} files...")

    except Exception as e:
        error_count += 1
        print(f"  ERR {fname[:40]:40s} {type(e).__name__}")

print(f"\nProcessed: {ok_count} OK, {error_count} errors")

if all_data:
    # Concatenate
    df_all = pd.concat(all_data, ignore_index=True)

    # Save as partitioned parquet
    pq_path = OUT_PARQUET / "lg18650_hg2_normalized.parquet"
    df_all.to_parquet(
        pq_path,
        engine='pyarrow',
        partition_cols=['cell_id', 'profile_type'],
        index=False,
        compression='snappy'
    )
    print(f"✓ Saved parquet: {pq_path}")
    print(f"  {len(df_all):,} total rows")

    # Save QA
    pd.DataFrame(qa_rows).to_csv(OUT_QA, index=False)
    print(f"✓ Saved QA: {OUT_QA}")

    # Summary
    train_eligible_count = sum(1 for qa in qa_rows if qa['train_eligible'])
    profiles = sorted(set(qa['profile_type'] for qa in qa_rows))

    with open(OUT_SUMMARY, 'w') as f:
        f.write("# LG18650_HG2 Full Normalization Summary\n\n")
        f.write(f"## Coverage\n")
        f.write(f"- **Files processed:** {ok_count}/{len(manifest_df)}\n")
        f.write(f"- **Total rows:** {len(df_all):,}\n")
        f.write(f"- **Profiles:** {', '.join(profiles)}\n\n")

        f.write("## Training Eligibility\n\n")
        f.write(f"- **Train eligible:** {train_eligible_count}\n")
        f.write(f"- **Not eligible:** {ok_count - train_eligible_count}\n\n")

        f.write("## SOC Method Distribution\n\n")
        methods = {}
        for qa in qa_rows:
            m = qa['soc_method']
            methods[m] = methods.get(m, 0) + 1
        for m in sorted(methods.keys()):
            f.write(f"- {m}: {methods[m]} files\n")

        f.write(f"\n## Issues Found\n\n")
        issues = {}
        for qa in qa_rows:
            issue = qa['issue']
            if issue != 'OK':
                issues[issue] = issues.get(issue, 0) + 1
        if issues:
            for issue in sorted(issues.keys()):
                f.write(f"- {issue}: {issues[issue]} files\n")
        else:
            f.write("- None\n")

        f.write(f"\n## Data Quality\n\n")
        f.write(f"- Parquet schema: dataset, cell_id, profile_type, temperature_condition, cycle_id, time_s, voltage_V, current_A, temperature_C, capacity_Ah, soc_target, soc_method, source_file, train_eligible, notes\n")
        f.write(f"- Partitioned by: cell_id, profile_type\n")
        f.write(f"- Compression: snappy\n\n")

        f.write("## Next\n\n")
        f.write("```bash\n")
        f.write("# Validate cross-dataset against Oxford\n")
        f.write("python3 scripts/validate_cross_dataset.py\n")
        f.write("```\n")

    print(f"✓ Saved summary: {OUT_SUMMARY}")

    print("\n" + "="*60)
    print("FULL NORMALIZATION COMPLETE")
    print("="*60)
else:
    print("No data processed")
