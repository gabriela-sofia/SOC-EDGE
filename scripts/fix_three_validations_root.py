from pathlib import Path
script = Path("scripts/run_method_b_post_sp2_three_validations_final.py")
txt = script.read_text(encoding="utf-8")

lines = txt.splitlines()
new_lines = []

for line in lines:
    if line.strip().startswith("ROOT ="):
        new_lines.append("ROOT = Path(__file__).resolve().parents[1]")
    else:
        new_lines.append(line)

script.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print("OK: ROOT corrigido para Path(__file__).resolve().parents[1]")
