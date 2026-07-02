"""ECS navigation audit (validation only — no app boot required).

Statically discovers every left-navigation link, cross-references each against
registered FastAPI route handlers (including dynamic f-string route loops) and
their rendered templates, and emits the audit artifacts.

Read-only: writes ONLY into nav_audit/. Does not import the app or touch logic.
"""
from __future__ import annotations

import csv
import json
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nav_audit"
TPL_DIRS = [ROOT / "modules"]

NAV_FILES = [
    ROOT / "modules/shared/templates/partials/ecs_nav_groups.html",
    ROOT / "modules/shared/templates/partials/ecs_nav_ai_sdlc.html",
]

# ----------------------------------------------------------------------------- #
# Phase 1 — discover nav links + hierarchy
# ----------------------------------------------------------------------------- #

HREF_RE = re.compile(r'href="([^"]+)"')
GROUP_LABEL_RE = re.compile(r'ecs-nav-group-label">([^<]+)<')


def clean_path(href: str) -> str:
    p = href.split("{{")[0].split("?")[0].strip()
    return p


def discover_nav():
    groups = OrderedDict()
    for f in NAV_FILES:
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        # split into groups by the group-label marker
        chunks = re.split(r'(<button class="ecs-nav-group-toggle)', text)
        current = "Ungrouped"
        # simpler: iterate lines, track current group label
        current = None
        for line in text.splitlines():
            lm = GROUP_LABEL_RE.search(line)
            if lm:
                current = lm.group(1).strip()
                groups.setdefault(current, [])
                continue
            for href in HREF_RE.findall(line):
                p = clean_path(href)
                if not p.startswith("/"):
                    continue
                grp = current or "Top"
                groups.setdefault(grp, [])
                # nested = grandchild (framework items / admin)
                nested = "ecs-sidebar-btn-nested" in line
                label_m = re.search(r'>([^<>{}]+?)\s*(?:{{|</a>)', line)
                label = (label_m.group(1).strip() if label_m else p)
                groups[grp].append({"label": label, "url": p, "nested": nested})
    return groups


# ----------------------------------------------------------------------------- #
# Phase 2 — registered routes (incl. dynamic loops) + template render
# ----------------------------------------------------------------------------- #

ROUTE_RE = re.compile(r'@(?:app|router)\.(?:get|post|api_route)\(\s*[\"\']([^\"\']+)')
# dynamic loop: @app.get(f"/mvp/ai-sdlc/{s}") with a nearby `for s in [...]`
FSTRING_ROUTE_RE = re.compile(r'@(?:app|router)\.get\(\s*f[\"\']([^\"\']+)')
LOOP_LIST_RE = re.compile(r'for\s+(\w+)\s+in\s+\[([^\]]+)\]')
TEMPLATE_RE = re.compile(r'TemplateResponse\(\s*(?:request\s*,\s*)?[\"\']([^\"\']+\.html)[\"\']')


def py_files():
    out = []
    for base in ("modules", "app"):
        out += list((ROOT / base).rglob("*.py"))
    out += list(ROOT.glob("*.py"))
    return out


def discover_routes():
    static = set()
    dynamic = []  # (template_pattern, [values])
    for f in py_files():
        try:
            s = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in ROUTE_RE.findall(s):
            static.add(m)
        # dynamic f-string routes registered inside a loop. Support both:
        #   for x in [ "a", "b" ]:        ... @app.get(f"/p/{x}")
        #   for x in SOME_DICT_OR_LIST:    ... @app.get(f"/p/{x}")  (resolve the name)
        for fm in re.finditer(
                r'for\s+(\w+)\s+in\s+([^\n:]+):\s*(?:#[^\n]*)?\n(?:[^\n]*\n){0,10}?\s*@(?:app|router)\.get\(\s*f[\"\']([^\"\']+)',
                s):
            var, iterable, pat = fm.group(1).strip(), fm.group(2).strip(), fm.group(3)
            vals = []
            if iterable.startswith("["):
                vals = re.findall(r'[\"\']([^\"\']+)[\"\']', iterable)
            else:
                # resolve a referenced list/dict literal defined in the same file
                name = iterable.split(".")[0].strip()
                dm = re.search(re.escape(name) + r'\s*=\s*[\[{](.*?)[\]}]', s, re.DOTALL)
                if dm:
                    vals = re.findall(r'[\"\']([^\"\']+)[\"\']\s*:', dm.group(1)) \
                        or re.findall(r'[\"\']([^\"\']+)[\"\']', dm.group(1))
            expanded = pat.replace("{" + var + "}", "{V}")
            if vals:
                dynamic.append((expanded, vals))
    return static, dynamic


def norm(p: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", p)


def route_matches(url: str, static: set, dynamic: list) -> bool:
    n = norm(url)
    snorm = {norm(s) for s in static}
    if n in snorm:
        return True
    # framework dynamic: /framework/{name}
    if n == "/framework/{}" or url.startswith("/framework/"):
        if any(norm(s) == "/framework/{}" for s in static):
            return True
    # dynamic loop routes — substitute any single {placeholder} with each value
    for pat, vals in dynamic:
        sub = re.sub(r"\{[^}]+\}", "{V}", pat)
        base = sub.replace("{V}", "")
        for v in vals:
            if url == sub.replace("{V}", v) or url.rstrip("/") == base.rstrip("/") + v:
                return True
    return False


def all_templates():
    names = {}
    for d in TPL_DIRS:
        for t in d.rglob("*.html"):
            names[t.name] = str(t.relative_to(ROOT))
    return names


def route_to_template():
    """Map each route path -> template filename it renders (best-effort, static)."""
    mapping = {}
    for f in py_files():
        try:
            s = f.read_text(encoding="utf-8")
        except Exception:
            continue
        # find each route decorator and the first TemplateResponse after it
        for m in re.finditer(r'@(?:app|router)\.get\(\s*f?[\"\']([^\"\']+)[\"\'][\s\S]{0,1200}?TemplateResponse\(\s*(?:request\s*,\s*)?[\"\']([^\"\']+\.html)', s):
            mapping[m.group(1)] = m.group(2)
    return mapping


def main():
    OUT.mkdir(exist_ok=True)
    groups = discover_nav()
    static, dynamic = discover_routes()
    tpls = all_templates()
    r2t = route_to_template()

    # Phase 1 artifact
    inv = {"groups": groups,
           "total_links": sum(len(v) for v in groups.values()),
           "total_groups": len(groups)}
    (OUT / "navigation_inventory.json").write_text(json.dumps(inv, indent=2), encoding="utf-8")

    # Phase 2 + 3 — audit each link (handler + template)
    rows = []
    for grp, items in groups.items():
        for it in items:
            url = it["url"]
            ok = route_matches(url, static, dynamic)
            tpl = r2t.get(url) or r2t.get(norm(url))
            # dynamic-loop routes share one template (mvp_ai_sdlc_worklist.html)
            tpl_status = "n/a"
            if tpl:
                tpl_status = "found" if tpl in tpls else "MISSING_TEMPLATE"
            status = "OK" if ok else "MISSING_ROUTE"
            if ok and tpl and tpl not in tpls:
                status = "MISSING_TEMPLATE"
            issue = "" if status == "OK" else (
                "No registered handler" if status == "MISSING_ROUTE" else f"Template {tpl} not found")
            rows.append({"menu": grp, "submenu": it["label"], "url": url,
                         "handler": "found" if ok else "none",
                         "template": tpl or "(dynamic/redirect)",
                         "template_status": tpl_status,
                         "level": 3 if it["nested"] else 2,
                         "status": status, "issue": issue})

    with (OUT / "navigation_click_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["menu", "submenu", "url", "handler",
                                            "template", "template_status", "level", "status", "issue"])
        w.writeheader()
        w.writerows(rows)

    # Phase 7 — dead links / orphans: handlers with no menu (informational)
    nav_urls = {norm(r["url"]) for r in rows}
    handler_urls = {norm(s) for s in static if s.startswith(("/mvp", "/dashboard", "/framework"))
                    and not s.startswith("/mvp/") or s.startswith(("/mvp/", "/dashboard", "/framework"))}
    orphans = sorted(u for u in handler_urls
                     if u not in nav_urls and "{" not in u
                     and not u.startswith("/api"))

    total = len(rows)
    okc = sum(1 for r in rows if r["status"] == "OK")
    tpl_known = [r for r in rows if r["template_status"] != "n/a"]
    tpl_ok = sum(1 for r in tpl_known if r["template_status"] == "found")
    summary = {
        "total_links": total, "ok": okc, "broken": total - okc,
        "navigation_health_pct": round(okc / total * 100, 1) if total else 0,
        "route_health_pct": round(okc / total * 100, 1) if total else 0,
        "template_health_pct": round(tpl_ok / len(tpl_known) * 100, 1) if tpl_known else 100.0,
        "demo_readiness_pct": round(okc / total * 100, 1) if total else 0,
        "static_routes": len(static), "dynamic_loops": len(dynamic),
        "orphan_handler_pages": orphans,
        "broken_list": [r for r in rows if r["status"] != "OK"],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in
          ("total_links", "ok", "broken", "navigation_health_pct", "template_health_pct",
           "demo_readiness_pct", "static_routes", "dynamic_loops")}, indent=2))
    print("orphan handler pages (reachable by URL, not in left nav):", len(orphans))
    if summary["broken_list"]:
        print("BROKEN:")
        for b in summary["broken_list"]:
            print(" ", b["menu"], "|", b["submenu"], "|", b["url"], "|", b["issue"])


if __name__ == "__main__":
    main()
