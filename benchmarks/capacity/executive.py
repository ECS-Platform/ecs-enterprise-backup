"""Executive capacity planner report (PART 8).

Produces an executive-level summary from capacity estimates: recommended GKE
nodes, pod requests/limits, Cloud SQL tier, GCS size, monthly + 5-year cost, the
top-5 bottlenecks / risks / cost-optimizations, and phase-wise sizing.

Outputs: Markdown, JSON, CSV, and an optional dependency-free HTML dashboard.
Pure formatting over the estimate dicts (no new estimation logic).
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

#: Phases surfaced in the executive phase-wise sizing table.
_EXEC_PHASES = ["demo", "phase1", "enterprise", "pan-bank", "large"]


def _row(estimate: dict[str, Any]) -> dict[str, Any]:
    from benchmarks.capacity.report import recommendation_row
    return recommendation_row(estimate)


def top_bottlenecks(estimate: dict[str, Any]) -> list[str]:
    """Top-5 likely bottlenecks derived from the estimate."""
    gke = estimate.get("gke_compute", {})
    pg = estimate.get("postgres_pgvector", {})
    net = estimate.get("network", {})
    ai = estimate.get("ai_throughput", {})
    logs = estimate.get("logging_monitoring", {})
    items = [
        f"GKE compute: peak ~{gke.get('peak_cores')} cores → "
        f"{gke.get('recommended_replicas')} replicas (scale the web tier).",
        f"Cloud SQL: {pg.get('recommended_cloud_sql', {}).get('tier')} — connection "
        f"limits + query load are the DB ceiling.",
        f"AI/RAG: single-stream ~{ai.get('prompts_per_second_single_stream')} prompts/s — "
        f"prompt concurrency is RAM-bound; use a dedicated RAG pool.",
        f"Cross-cloud egress: ~{net.get('cross_cloud_aws_gcp_gib_per_month')} GiB/mo "
        f"(AWS Net Banking ↔ GCP) — bandwidth + cost.",
        f"Cloud Logging: ~{logs.get('per_day_gib', {}).get('total')} GiB/day ingestion.",
    ]
    return items[:5]


def top_risks(estimate: dict[str, Any]) -> list[str]:
    k8s = estimate.get("kubernetes", {})
    pg = estimate.get("postgres_pgvector", {})
    dur = estimate.get("db_durability", {})
    ev = (k8s.get("eviction_risk", {}) or {}).get("risk", "unknown")
    return [
        f"Pod eviction/OOM risk: {ev} — size memory requests ≥ working set.",
        f"DB slow-query risk: {(dur.get('performance', {}) or {}).get('slow_query_risk', 'n/a')} "
        f"at {pg.get('storage_gib', {}).get('year_1_total')} GiB year-1.",
        "State externalization required before multi-replica scaling (in-memory ecs_state).",
        "Cross-cloud connectivity + IAM must be least-privilege and monitored.",
        "Backups/PITR + restore drills required for banking retention/DR.",
    ][:5]


def top_optimizations(estimate: dict[str, Any]) -> list[str]:
    det = estimate.get("object_storage_detail", {})
    tp = (det.get("throughput", {}) or {})
    return [
        "GCS lifecycle tiering (Nearline/Coldline/Archive) for cold evidence — "
        "large storage cost reduction.",
        f"Compression on evidence (~{tp.get('compression_savings_pct')}% savings where compressible).",
        "Committed-use discounts / autoscaling to match compute to real demand.",
        "PgBouncer + read replicas to right-size Cloud SQL vCPU.",
        "Batch small object writes + multipart large uploads to cut GCS op costs.",
    ][:5]


def build(estimates: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble the executive planner data structure from estimates."""
    by_key = {e["profile"]["key"]: e for e in estimates}
    rows = [_row(e) for e in estimates]
    # Use the largest available profile for headline bottlenecks/risks.
    headline = max(estimates, key=lambda e: e["profile"]["apps"]) if estimates else {}
    phase_rows = [_row(by_key[k]) for k in _EXEC_PHASES if k in by_key]
    return {
        "report": "ecs_executive_capacity_planner",
        "profiles": [e["profile"]["key"] for e in estimates],
        "sizing_table": rows,
        "phase_wise_sizing": phase_rows,
        "top_bottlenecks": top_bottlenecks(headline) if headline else [],
        "top_risks": top_risks(headline) if headline else [],
        "top_cost_optimizations": top_optimizations(headline) if headline else [],
        "_disclaimer": "Executive estimate — documented assumptions × profiles; cost rates "
                       "illustrative. Calibrate before spend decisions.",
    }


def to_json(estimates: list[dict[str, Any]]) -> str:
    return json.dumps(build(estimates), indent=2, default=str)


def to_csv(estimates: list[dict[str, Any]]) -> str:
    data = build(estimates)
    rows = data["sizing_table"]
    if not rows:
        return ""
    cols = ["profile", "name", "apps", "replicas", "gke_nodes", "gke_node_type",
            "pod_cpu_request", "pod_memory_request", "cloud_sql_tier",
            "cloud_sql_storage_gib", "gcs_year1_gib", "gcs_year5_gib",
            "cost_monthly", "cost_annual", "cost_5yr"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def to_markdown(estimates: list[dict[str, Any]]) -> str:
    data = build(estimates)
    lines = ["# ECS Executive Capacity Planner\n",
             f"> {data['_disclaimer']}\n",
             "## Recommended sizing\n",
             "| Profile | Apps | GKE (repl×nodes) | Pod CPU/Mem | Cloud SQL | GCS y1 | GCS y5 | Cost/mo | Cost 5y |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in data["sizing_table"]:
        lines.append(
            f"| {r['name']} | {r['apps']} | {r['replicas']}×{r['gke_nodes']} {r['gke_node_type']} | "
            f"{r['pod_cpu_request']}/{r['pod_memory_request']} | {r['cloud_sql_tier']} | "
            f"{r['gcs_year1_gib']} GiB | {r['gcs_year5_gib']} GiB | "
            f"{r.get('cost_monthly')} | {r.get('cost_5yr')} |")

    if data["phase_wise_sizing"]:
        lines += ["\n## Phase-wise sizing\n",
                  "| Phase | Apps | Replicas | Nodes | Cloud SQL | GCS y5 | Cost/mo |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in data["phase_wise_sizing"]:
            lines.append(f"| {r['name']} | {r['apps']} | {r['replicas']} | {r['gke_nodes']} | "
                         f"{r['cloud_sql_tier']} | {r['gcs_year5_gib']} GiB | {r.get('cost_monthly')} |")

    def bullet(title, items):
        return [f"\n## {title}\n"] + [f"{i}. {x}" for i, x in enumerate(items, 1)]

    lines += bullet("Top 5 bottlenecks", data["top_bottlenecks"])
    lines += bullet("Top 5 risks", data["top_risks"])
    lines += bullet("Top 5 cost optimizations", data["top_cost_optimizations"])
    return "\n".join(lines)


def to_html(estimates: list[dict[str, Any]]) -> str:
    """Dependency-free single-file HTML dashboard."""
    data = build(estimates)

    def table(rows, cols):
        if not rows:
            return "<p>(no data)</p>"
        head = "".join(f"<th>{c}</th>" for c, _ in cols)
        body = ""
        for r in rows:
            body += "<tr>" + "".join(f"<td>{r.get(k, '')}</td>" for k, _ in cols) + "</tr>"
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    sizing_cols = [("name", "Profile"), ("apps", "Apps"), ("replicas", "Replicas"),
                   ("gke_nodes", "Nodes"), ("cloud_sql_tier", "Cloud SQL"),
                   ("gcs_year5_gib", "GCS y5 GiB"), ("cost_monthly", "Cost/mo"),
                   ("cost_5yr", "Cost 5y")]

    def ul(items):
        return "<ol>" + "".join(f"<li>{x}</li>" for x in items) + "</ol>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>ECS Executive Capacity Planner</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;margin:2rem;color:#1a2733;max-width:1100px}}
 h1{{color:#0b3d5c}} h2{{color:#0b3d5c;border-bottom:1px solid #dde;padding-bottom:.25rem}}
 table{{border-collapse:collapse;width:100%;margin:.5rem 0}}
 th,td{{border:1px solid #cbd5e0;padding:.4rem .6rem;text-align:left;font-size:.9rem}}
 th{{background:#eef4f8}} .note{{color:#666;font-size:.85rem}}
 ol{{line-height:1.6}}
</style></head><body>
<h1>ECS Executive Capacity Planner</h1>
<p class="note">{data['_disclaimer']}</p>
<h2>Recommended sizing</h2>
{table(data['sizing_table'], sizing_cols)}
<h2>Phase-wise sizing</h2>
{table(data['phase_wise_sizing'], sizing_cols)}
<h2>Top 5 bottlenecks</h2>{ul(data['top_bottlenecks'])}
<h2>Top 5 risks</h2>{ul(data['top_risks'])}
<h2>Top 5 cost optimizations</h2>{ul(data['top_cost_optimizations'])}
</body></html>"""


def write_executive(estimates: list[dict[str, Any]], out_dir: str, *,
                    basename: str = "executive", html: bool = False) -> dict[str, str]:
    """Write executive MD + JSON + CSV (+ optional HTML). Returns written paths."""
    import os

    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "markdown": os.path.join(out_dir, f"{basename}.md"),
        "json": os.path.join(out_dir, f"{basename}.json"),
        "csv": os.path.join(out_dir, f"{basename}.csv"),
    }
    with open(paths["markdown"], "w", encoding="utf-8") as fh:
        fh.write(to_markdown(estimates))
    with open(paths["json"], "w", encoding="utf-8") as fh:
        fh.write(to_json(estimates))
    with open(paths["csv"], "w", encoding="utf-8") as fh:
        fh.write(to_csv(estimates))
    if html:
        paths["html"] = os.path.join(out_dir, f"{basename}.html")
        with open(paths["html"], "w", encoding="utf-8") as fh:
            fh.write(to_html(estimates))
    return paths
