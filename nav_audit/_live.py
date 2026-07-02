"""Real HTTP validation of every ECS navigation link against the running server."""
from __future__ import annotations

import csv
import json
import re
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nav_audit"
BASE = "http://127.0.0.1:8000"

inv = json.loads((OUT / "navigation_inventory.json").read_text())

# Real framework names to expand the /framework/{{framework}} nav loop.
FRAMEWORKS = ["PCI-DSS", "ISO27001", "SOC2", "RBI-CSF", "AI-SDLC"]

urls = []
seen = set()
for grp, items in inv["groups"].items():
    for it in items:
        u = it["url"]
        # The framework menu uses a Jinja loop href (/framework/ base only after
        # static stripping). Expand it to the real per-framework pages.
        if u.rstrip("/") == "/framework":
            for fw in FRAMEWORKS:
                fu = f"/framework/{fw}"
                if fu not in seen:
                    seen.add(fu)
                    urls.append((grp, f"{it['label']} — {fw}", fu))
            continue
        if u not in seen:
            seen.add(u)
            urls.append((grp, it["label"], u))

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
NAV_RE = re.compile(r'ecs-nav-group|ecs-sidebar-btn|ecs-sidebar', re.I)


def fetch(url):
    req = urllib.request.Request(BASE + url, headers={"User-Agent": "ecs-nav-qa"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        return e.code, body
    except Exception as e:  # connection / timeout
        return 0, f"__ERR__ {e}"


def strip(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


rows = []
passed = 0
for grp, label, url in urls:
    code, body = fetch(url)
    title = ""
    tm = TITLE_RE.search(body)
    if tm:
        title = strip(tm.group(1))[:80]
    if not title:
        hm = H1_RE.search(body)
        if hm:
            title = strip(hm.group(1))[:80]
    nav_ok = bool(NAV_RE.search(body))
    content_len = len(strip(body))
    # render checks
    issues = []
    if code == 0:
        issues.append("connection_error")
    elif code == 401:
        issues.append("401_unauthorized")
    elif code == 403:
        issues.append("403_forbidden")
    elif code == 404:
        issues.append("404_not_found")
    elif code >= 500:
        issues.append(f"{code}_server_error")
    elif code != 200:
        issues.append(f"http_{code}")
    if code == 200:
        if content_len < 400:
            issues.append("blank_or_thin_page")
        if not title:
            issues.append("no_title")
        if not nav_ok:
            issues.append("nav_missing")
    # jinja/undefined leak detection
    if "jinja2" in body.lower() and "traceback" in body.lower():
        issues.append("jinja_error")
    render = "OK" if (code == 200 and not issues) else "FAIL"
    if render == "OK":
        passed += 1
    rows.append({"menu": grp, "submenu": label, "url": url, "http_status": code,
                 "page_title": title or "(none)", "content_chars": content_len,
                 "nav_visible": "yes" if nav_ok else "no",
                 "render_status": render, "issue": ";".join(issues) or ""})

with (OUT / "navigation_live_validation.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["menu", "submenu", "url", "http_status", "page_title",
                                        "content_chars", "nav_visible", "render_status", "issue"])
    w.writeheader()
    w.writerows(rows)

total = len(rows)
fails = [r for r in rows if r["render_status"] != "OK"]
print(json.dumps({
    "pages_tested": total, "pages_passed": passed, "pages_failed": len(fails),
    "success_pct": round(passed / total * 100, 1) if total else 0,
}, indent=2))
if fails:
    print("FAILURES:")
    for f in fails:
        print(f"  {f['http_status']:>3} {f['url']}  [{f['issue']}]")
