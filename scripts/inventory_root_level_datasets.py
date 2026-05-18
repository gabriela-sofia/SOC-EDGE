from pathlib import Path
import pandas as pd
import zipfile
import json

ROOT = Path(".")

rows = []
top_dirs = [p for p in ROOT.iterdir() if p.is_dir()]

for d in top_dirs:
    files = [p for p in d.rglob("*") if p.is_file()]
    dirs = [p for p in d.rglob("*") if p.is_dir()]
    suffix_counts = {}
    total_mb = 0.0
    zip_status = []

    for f in files:
        suffix = f.suffix.lower() or "<no_ext>"
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
        try:
            total_mb += f.stat().st_size / (1024 * 1024)
        except Exception:
            pass

        if suffix == ".zip":
            try:
                zstat = "zip_valid" if zipfile.is_zipfile(f) else "zip_corrupted"
            except Exception:
                zstat = "zip_check_error"
            zip_status.append(f"{f.name}:{zstat}")

    sample_files = [str(f.relative_to(ROOT)).replace("\\", "/") for f in files[:15]]

    rows.append({
        "top_dir": d.name,
        "n_files": len(files),
        "n_dirs": len(dirs),
        "total_mb": round(total_mb, 3),
        "suffix_counts": json.dumps(suffix_counts, ensure_ascii=False),
        "zip_status": "; ".join(zip_status),
        "sample_files": " | ".join(sample_files),
    })

df = pd.DataFrame(rows).sort_values(["total_mb", "n_files"], ascending=False)

out = Path("outputs/external_datasets/root_level_dataset_inventory.csv")
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)

print(f"OK: {out}")
print(df[["top_dir","n_files","n_dirs","total_mb","suffix_counts","zip_status"]].to_string(index=False))
