"""Build navigation_matrix.csv (requested columns) + broken_routes.md from the
live validation results, enriched with the statically-resolved template name."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nav_audit"

spec = importlib.util.spec_from_file_location("_audit", OUT / "_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
r2t = audit.route_to_template()


def tpl_for(url: str) -> str:
    return r2t.get(url) or r2t.get(audit.norm(url)) or ""


live = list(csv.DictReader((OUT / "navigation_live_validation.csv").open()))

rows = []
broken = []
for r in live:
    url = r["url"]
    tpl = tpl_for(url)
    if not tpl:
        if url.startswith("/framework/"):
            tpl = "mvp_framework.html"
        elif url.startswith("/mvp/ai-sdlc/"):
            tpl = "mvp_ai_sdlc_worklist.html"
        else:
            tpl = "(shared/handler)"
    working = "Y" if r["render_status"] == "OK" and r["http_status"] == "200" else "N"
    comments = "" if working == "Y" else r["issue"]
    if working == "Y" and r["nav_visible"] != "yes":
        comments = "nav not detected"
    rows.append({
        "Menu": r["menu"], "Submenu": r["submenu"], "Route": url,
        "HTTP Status": r["http_status"], "Template": tpl,
        "Working(Y/N)": working, "Comments": comments or "OK",
    })
    if working == "N":
        broken.append(rows[-1])

with (OUT / "navigation_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["Menu", "Submenu", "Route", "HTTP Status",
                                        "Template", "Working(Y/N)", "Comments"])
    w.writeheader()
    w.writerows(rows)

md = ["# Broken Navigation Routes", ""]
if not broken:
    md.append("**No broken routes.** All %d navigation routes return HTTP 200 and render successfully." % len(rows))
else:
    md.append("| Menu | Submenu | Route | HTTP | Issue |")
    md.append("|---|---|---|---|---|")
    for b in broken:
        md.append(f"| {b['Menu']} | {b['Submenu']} | {b['Route']} | {b['HTTP Status']} | {b['Comments']} |")
(OUT / "broken_routes.md").write_text("\n".join(md) + "\n", encoding="utf-8")

print("rows:", len(rows), "broken:", len(broken))
