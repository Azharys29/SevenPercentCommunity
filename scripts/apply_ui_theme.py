from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = '<link rel="stylesheet" href="./ui.css">'

changed = 0
for path in sorted(ROOT.glob("*.html")):
    text = path.read_text(encoding="utf-8")
    if LINK in text:
        continue
    marker = "</head>"
    if marker not in text:
        continue
    text = text.replace(marker, f"{LINK}\n{marker}", 1)
    path.write_text(text, encoding="utf-8")
    changed += 1

print(f"UI theme linked on {changed} HTML pages.")
