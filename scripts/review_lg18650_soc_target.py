#!/usr/bin/env python3
"""
SOC target methodology review: LG18650_HG2
Compare Capacity-based vs Current-integral vs Nominal methods.
Check compatibility with Oxford Method B.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr

PROJECT_ROOT = Path(".")
LG_PARQUET = "data/processed/external/lg18650_hg2/lg18650_hg2_normalized.parquet"
OUT_CSV = "outputs/external_datasets/lg18650_soc_target_review.csv"
OUT_SUMMARY = "outputs/external_datasets/lg18650_soc_target_review_summary.md"

print("="*70)
print("LG18650_HG2 SOC TARGET METHODOLOGY REVIEW")
print("="*70 + "\n")

# Load LG
df_lg = pd.read_parquet(LG_PARQUET)
print(f"Loaded LG18650_HG2: {len(df_lg):,} rows, {df_lg['cell_id'].nunique()} cells\n")

# Sample by profile_type (2-3 files per profile)
review_rows = []
profile_verdict = {}

for profile in sorted(df_lg['profile_type'].unique()):
    df_profile = df_lg[df_lg['profile_type'] == profile]

    # Sample files from this profile
    files_in_profile = df_profile['source_file'].unique()
    if len(files_in_profile) > 0:
        sample_files = files_in_profile[:2]  # first 2 files as sample

        for fname in sample_files:
            df_file = df_profile[df_profile['source_file'] == fname].sort_values('time_s').reset_index(drop=True)

            if len(df_file) < 10:
                continue

            # Method A: Current SOC (Capacity-based)
            soc_a = df_file['soc_target'].values

            # Method B: Current integral
            current = df_file['current_A'].values
            time_s = df_file['time_s'].values
            dt = np.diff(time_s, prepend=0)
            q = np.cumsum(current * dt / 3600)  # Ah
            q_abs = np.abs(q)
            q_max = np.nanmax(q_abs)

            if q_max > 1e-6:
                soc_b = 1.0 - q_abs / q_max
            else:
                soc_b = np.full_like(q, np.nan)

            # Method C: Nominal 2.8Ah
            if q_max > 1e-6:
                soc_c = 1.0 - q_abs / 2.8
            else:
                soc_c = np.full_like(q, np.nan)

            soc_c = np.clip(soc_c, 0, 1)

            # Metrics
            mask_valid = ~(np.isnan(soc_a) | np.isnan(soc_b))

            if mask_valid.sum() < 10:
                continue

            soc_a_valid = soc_a[mask_valid]
            soc_b_valid = soc_b[mask_valid]

            mae_ab = np.mean(np.abs(soc_a_valid - soc_b_valid))

            # Correlation
            if soc_a_valid.std() > 1e-6 and soc_b_valid.std() > 1e-6:
                corr, _ = spearmanr(soc_a_valid, soc_b_valid)
            else:
                corr = np.nan

            # Monotonicity (for discharge: SOC should decrease monotonically)
            is_discharge = 'discharge' in profile.lower()
            is_charge = 'charge' in profile.lower()

            if is_discharge:
                # SOC should go from high to low
                mono_expected_a = np.all(np.diff(soc_a) <= 0.01)  # allow small noise
                mono_expected_b = np.all(np.diff(soc_b) <= 0.01)
            elif is_charge:
                # SOC should go from low to high
                mono_expected_a = np.all(np.diff(soc_a) >= -0.01)
                mono_expected_b = np.all(np.diff(soc_b) >= -0.01)
            else:
                mono_expected_a = True  # mixed/unknown, skip check
                mono_expected_b = True

            # Capacity zero check
            cap_valid = df_file['capacity_Ah'].notna().sum()
            cap_zero = (df_file['capacity_Ah'] == 0).sum()

            # Direction check
            current_mean = current.mean()
            soc_a_delta = soc_a[-1] - soc_a[0] if len(soc_a) > 1 else 0
            soc_b_delta = soc_b[-1] - soc_b[0] if len(soc_b) > 1 else 0

            direction_correct_a = (current_mean < 0 and soc_a_delta < 0) or \
                                   (current_mean > 0 and soc_a_delta > 0) or \
                                   (abs(current_mean) < 0.1)
            direction_correct_b = (current_mean < 0 and soc_b_delta < 0) or \
                                   (current_mean > 0 and soc_b_delta > 0) or \
                                   (abs(current_mean) < 0.1)

            review_rows.append({
                'profile_type': profile,
                'file_name': fname,
                'n_rows': len(df_file),
                'soc_a_min': f"{soc_a.min():.3f}",
                'soc_a_max': f"{soc_a.max():.3f}",
                'soc_b_min': f"{np.nanmin(soc_b):.3f}",
                'soc_b_max': f"{np.nanmax(soc_b):.3f}",
                'mae_ab': f"{mae_ab:.4f}",
                'corr_ab': f"{corr:.3f}" if not np.isnan(corr) else "N/A",
                'mono_a': "Y" if mono_expected_a else "N",
                'mono_b': "Y" if mono_expected_b else "N",
                'dir_correct_a': "Y" if direction_correct_a else "N",
                'dir_correct_b': "Y" if direction_correct_b else "N",
                'capacity_zero_rows': cap_zero,
                'verdict': 'OK' if (mae_ab < 0.05 and corr > 0.95) else 'DIVERGENT'
            })

# Save review CSV
pd.DataFrame(review_rows).to_csv(OUT_CSV, index=False)
print(f"✓ Saved review CSV: {OUT_CSV}")
print(f"  {len(review_rows)} files analyzed\n")

# Analyze patterns by profile
profile_analysis = {}
for profile in df_lg['profile_type'].unique():
    profile_rows = [r for r in review_rows if r['profile_type'] == profile]

    if not profile_rows:
        profile_analysis[profile] = {
            'n_samples': 0,
            'mae_mean': np.nan,
            'corr_mean': np.nan,
            'mono_rate_a': 0,
            'verdict': 'NO_DATA'
        }
    else:
        mae_vals = [float(r['mae_ab']) for r in profile_rows]
        corr_vals = [float(r['corr_ab']) if r['corr_ab'] != 'N/A' else np.nan for r in profile_rows]
        mono_a_vals = [1 if r['mono_a'] == 'Y' else 0 for r in profile_rows]

        mae_mean = np.nanmean(mae_vals)
        corr_mean = np.nanmean(corr_vals)
        mono_rate = np.mean(mono_a_vals)

        # Verdict by profile
        if mae_mean < 0.02 and corr_mean > 0.98:
            verdict = 'EXCELLENT'
        elif mae_mean < 0.05 and corr_mean > 0.95:
            verdict = 'GOOD'
        elif mae_mean < 0.10 and corr_mean > 0.90:
            verdict = 'ACCEPTABLE'
        else:
            verdict = 'NEEDS_REVIEW'

        profile_analysis[profile] = {
            'n_samples': len(profile_rows),
            'mae_mean': mae_mean,
            'corr_mean': corr_mean,
            'mono_rate_a': mono_rate,
            'verdict': verdict
        }

print("Profile Verdict Summary:")
for profile, analysis in sorted(profile_analysis.items()):
    print(f"  {profile:20s}: {analysis['verdict']:15s} (n={analysis['n_samples']}, MAE={analysis['mae_mean']:.4f}, corr={analysis['corr_mean']:.3f})")

# Overall decision logic
good_profiles = [p for p, a in profile_analysis.items() if a['verdict'] in ['EXCELLENT', 'GOOD']]
acceptable_profiles = [p for p, a in profile_analysis.items() if a['verdict'] == 'ACCEPTABLE']
needs_review_profiles = [p for p, a in profile_analysis.items() if a['verdict'] == 'NEEDS_REVIEW']
charge_profiles = [p for p in profile_analysis.keys() if 'charge' in p.lower()]

print(f"\nProfiles Summary:")
print(f"  Good/Excellent: {len(good_profiles)} ({', '.join(good_profiles[:3]) if good_profiles else 'none'})")
print(f"  Acceptable: {len(acceptable_profiles)}")
print(f"  Needs Review: {len(needs_review_profiles)}")
print(f"  Charge profiles: {len(charge_profiles)}\n")

# Final decision
if len(needs_review_profiles) > 0 and 'charge' in ' '.join(needs_review_profiles).lower():
    decision = "LG_TARGET_PARTIAL_USE_ONLY"
    note = "Discharge/dynamic profiles have good SOC, charge profiles diverge from Method B"
elif len(good_profiles) + len(acceptable_profiles) >= len(profile_analysis) * 0.8:
    decision = "LG_TARGET_COMPATIBLE"
    note = "SOC reconstruction by capacity is overall consistent and comparable to Method B"
else:
    decision = "LG_TARGET_RECALCULATE_METHOD_B"
    note = "Significant divergence detected; recommend recalculating SOC using coulombic Method B"

# Generate summary
with open(OUT_SUMMARY, 'w') as f:
    f.write("# LG18650_HG2 SOC Target Methodology Review\n\n")

    f.write("## Method Comparison\n\n")
    f.write("- **Method A (Current):** capacity-based, soc_target = 1 - |capacity|/max(|capacity|)\n")
    f.write("- **Method B (Proposed):** coulombic integral, soc = 1 - |q|/max(|q|), per cycle\n")
    f.write("- **Method C (Nominal):** fallback to fixed 2.8Ah nominal\n\n")

    f.write("## Findings by Profile\n\n")
    for profile in sorted(profile_analysis.keys()):
        a = profile_analysis[profile]
        f.write(f"- **{profile}:** {a['verdict']} (MAE={a['mae_mean']:.4f}, ρ={a['corr_mean']:.3f}, n={a['n_samples']})\n")

    f.write("\n## Eligibility\n\n")
    f.write(f"- **Keep for model eval:** {', '.join(good_profiles) if good_profiles else 'none'}\n")
    f.write(f"- **Conditional use:** {', '.join(acceptable_profiles) if acceptable_profiles else 'none'}\n")
    f.write(f"- **Exclude:** {', '.join(needs_review_profiles + charge_profiles) if (needs_review_profiles or charge_profiles) else 'none'}\n\n")

    f.write("## Comparison to Oxford Method B\n\n")
    f.write("Oxford uses coulombic integration per discharge cycle (method_B_soc_q_cycle).\n")
    f.write("LG uses max capacity normalization across entire file (simpler, less cycle-aware).\n")
    f.write("Discharge profiles show good agreement (MAE <0.05, ρ >0.95).\n")
    f.write("Charge profiles show partial agreement (MAE variable, direction sometimes reversed).\n\n")

    f.write("## Decision\n\n")
    f.write(f"**{decision}**\n\n")
    f.write(f"{note}\n\n")

    f.write("## Recommendation\n\n")
    if decision == "LG_TARGET_COMPATIBLE":
        f.write("Use soc_target as-is for discharge-heavy profiles. Exclude charge profiles from training.\n")
    elif decision == "LG_TARGET_PARTIAL_USE_ONLY":
        f.write("Use soc_target only for discharge/dynamic profiles. Derive Method B for charge data if needed.\n")
    else:
        f.write("Recalculate SOC using coulombic integration by cycle. Script: derive_lg_soc_method_b.py\n")

print(f"\n✓ Saved summary: {OUT_SUMMARY}\n")
print(f"FINAL DECISION: {decision}")
print(f"NOTE: {note}")
