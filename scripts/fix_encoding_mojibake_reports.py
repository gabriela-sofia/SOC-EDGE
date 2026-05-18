from pathlib import Path
import shutil

ROOT = Path(".")
TARGETS = [
    "REPORTS/26_IOT_MLP_FIRMWARE_PACKAGE_QA.md",
    "REPORTS/25_IOT_MLP_FIRMWARE_EXPORT_REPORT.md",
    "REPORTS/24_ESP32_INPUT_VALIDATION_SPEC.md",
    "REPORTS/FIRMWARE_HANDOFF_GUIDE.md",
    "REPORTS/27_FIRMWARE_PACKAGE_FINAL_DOCS_PATCH.md",
]

TARGETS += [str(p) for p in Path("handoff_esp32_soc_method_b_v1").rglob("*.md") if p.exists()]

def mojibake_score(s: str) -> int:
    markers = ["Ã", "Â", "âœ", "â€”", "â†", "â”", "Ã§", "Ã£", "Ã©", "Ã³"]
    return sum(s.count(m) for m in markers)

def fix_text(text: str) -> str:
    original_score = mojibake_score(text)

    # Melhor correção para UTF-8 lido como CP1252
    try:
        candidate = text.encode("cp1252").decode("utf-8")
        if mojibake_score(candidate) < original_score:
            return candidate
    except Exception:
        pass

    # Fallback pontual
    replacements = {
        "Ã¡": "á", "Ã ": "à", "Ã¢": "â", "Ã£": "ã",
        "Ã©": "é", "Ãª": "ê",
        "Ã­": "í",
        "Ã³": "ó", "Ã´": "ô", "Ãµ": "õ",
        "Ãº": "ú",
        "Ã§": "ç",
        "Ã‡": "Ç",
        "Ãƒ": "Ã",
        "Â°C": "°C",
        "Â±": "±",
        "âœ…": "✅",
        "âœ“": "✓",
        "âœ—": "✗",
        "â€”": "—",
        "â€“": "–",
        "â†’": "→",
        "â”œ": "├",
        "â”€": "─",
        "â”‚": "│",
        "â””": "└",
    }

    fixed = text
    for bad, good in replacements.items():
        fixed = fixed.replace(bad, good)

    # Segunda passada para casos tipo DECISÃƒO -> DECISÃO
    try:
        candidate = fixed.encode("cp1252").decode("utf-8")
        if mojibake_score(candidate) < mojibake_score(fixed):
            fixed = candidate
    except Exception:
        pass

    return fixed

rows = []
for rel in TARGETS:
    path = ROOT / rel
    if not path.exists():
        rows.append((rel, "MISSING", "", ""))
        continue

    text = path.read_text(encoding="utf-8", errors="replace")
    before = mojibake_score(text)
    fixed = fix_text(text)
    after = mojibake_score(fixed)

    if fixed != text:
        backup = path.with_suffix(path.suffix + ".bak_encoding")
        shutil.copy2(path, backup)
        path.write_text(fixed, encoding="utf-8", newline="\n")
        status = "FIXED"
    else:
        status = "UNCHANGED"

    rows.append((rel, status, before, after))

out = ROOT / "outputs/external_datasets/encoding_mojibake_fix_status.csv"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    "file,status,mojibake_before,mojibake_after\n" +
    "\n".join(f"{a},{b},{c},{d}" for a,b,c,d in rows),
    encoding="utf-8"
)

report = ROOT / "REPORTS/28_ENCODING_MOJIBAKE_FIX_REPORT.md"
report.write_text(
    "# Encoding/Mojibake Fix Report\n\n"
    "Correção de mojibake UTF-8/CP1252 aplicada aos relatórios e arquivos de handoff.\n\n"
    "| File | Status | Before | After |\n"
    "|---|---:|---:|---:|\n" +
    "\n".join(f"| `{a}` | {b} | {c} | {d} |" for a,b,c,d in rows) +
    "\n\nDecisão: ENCODING_MOJIBAKE_FIX_APPLIED\n",
    encoding="utf-8"
)

print("OK:", out)
print("OK:", report)
for r in rows:
    print(r)
