from pathlib import Path
import os, zipfile, json
import pandas as pd

ROOT = Path(".")
SCAN_DIRS = [
    ROOT / "data",
    ROOT / "outputs",
    ROOT / "REPORTS",
    ROOT / "models_external",
    ROOT / "handoff_esp32",
]

rows = []

for base in SCAN_DIRS:
    if not base.exists():
        continue

    for p in base.rglob("*"):
        try:
            if p.is_file():
                size_mb = p.stat().st_size / (1024 * 1024)
                suffix = p.suffix.lower()
                status = "file"

                if suffix == ".zip":
                    try:
                        status = "zip_valid" if zipfile.is_zipfile(p) else "zip_corrupted_or_incomplete"
                    except Exception:
                        status = "zip_check_error"

                rows.append({
                    "path": str(p).replace("\\", "/"),
                    "parent": str(p.parent).replace("\\", "/"),
                    "name": p.name,
                    "suffix": suffix,
                    "size_mb": round(size_mb, 3),
                    "status": status,
                })
            elif p.is_dir():
                try:
                    n_items = sum(1 for _ in p.iterdir())
                except Exception:
                    n_items = None

                if n_items == 0:
                    rows.append({
                        "path": str(p).replace("\\", "/"),
                        "parent": str(p.parent).replace("\\", "/"),
                        "name": p.name,
                        "suffix": "",
                        "size_mb": 0,
                        "status": "empty_dir",
                    })
        except Exception as e:
            rows.append({
                "path": str(p).replace("\\", "/"),
                "parent": str(p.parent).replace("\\", "/"),
                "name": p.name,
                "suffix": "",
                "size_mb": None,
                "status": f"scan_error:{e}",
            })

df = pd.DataFrame(rows)
out_dir = ROOT / "outputs" / "external_datasets"
out_dir.mkdir(parents=True, exist_ok=True)

out_csv = out_dir / "project_scientific_asset_inventory.csv"
df.to_csv(out_csv, index=False)

summary = {
    "total_items": int(len(df)),
    "by_suffix": df["suffix"].value_counts(dropna=False).to_dict() if len(df) else {},
    "by_status": df["status"].value_counts(dropna=False).to_dict() if len(df) else {},
    "largest_files": df.sort_values("size_mb", ascending=False).head(20)[["path","size_mb","status"]].to_dict(orient="records") if len(df) else [],
}

out_json = out_dir / "project_scientific_asset_inventory_summary.json"
out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"OK: {out_csv}")
print(f"OK: {out_json}")
print("By status:")
print(df["status"].value_counts(dropna=False).to_string())
print("\nLargest files:")
print(df.sort_values("size_mb", ascending=False).head(20)[["path","size_mb","status"]].to_string(index=False))
