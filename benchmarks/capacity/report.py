"""Report generation for the ECS GCP capacity-sizing benchmark.

Turns one or more capacity estimates (from ``sizing.estimate_capacity``) into:
  * a JSON report (full detail),
  * a Markdown sizing report (human-readable, with a recommendation table),
  * a CSV summary (one row per profile), and
  * a recommendation table (list-of-dict, reused by both Markdown and CSV).

Pure formatting — no estimation logic here.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def recommendation_row(estimate: dict[str, Any]) -> dict[str, Any]:
    """One flat recommendation row (the key sizing outputs) for a profile."""
    p = estimate["profile"]
    gke = estimate["gke_compute"]
    nodes = estimate["node_pool"]
    pg = estimate["postgres_pgvector"]
    gcs = estimate["gcs_object_storage"]
    logs = estimate["logging_monitoring"]
    return {
        "profile": p["key"],
        "name": p["name"],
        "apps": p["apps"],
        "frameworks": p["frameworks"],
        "total_controls": p["total_controls"],
        "total_evidences": p["total_evidences"],
        "connector_runs_per_day": p["connector_runs_per_day"],
        "prompt_runs_per_day": p["prompt_runs_per_day"],
        "avg_evidence_size_kb": p["avg_evidence_size_kb"],
        "retention_years": p["retention_years"],
        "peak_cores": gke["peak_cores"],
        "peak_ram_mib": gke["peak_ram_mib"],
        "pod_cpu_request": gke["recommended_pod"]["cpu_request"],
        "pod_memory_request": gke["recommended_pod"]["memory_request"],
        "replicas": gke["recommended_replicas"],
        "gke_nodes": nodes["recommended_nodes"],
        "gke_node_type": nodes["node_machine_type"],
        "cloud_sql_tier": pg["recommended_cloud_sql"]["tier"],
        "cloud_sql_storage_gib": pg["recommended_cloud_sql"]["storage_gib"],
        "db_year1_gib": pg["storage_gib"]["year_1_total"],
        "db_year5_gib": pg["storage_gib"]["year_5_total"],
        "gcs_year1_gib": gcs["year_1_total_gib"],
        "gcs_year5_gib": gcs["year_5_total_gib"],
        "logs_per_day_gib": logs["per_day_gib"]["total"],
        "logs_per_year_gib": logs["per_year_gib"],
        "cost_monthly": (estimate.get("cost") or {}).get("monthly_total"),
        "cost_annual": (estimate.get("cost") or {}).get("annual_total"),
        "cost_5yr": (estimate.get("cost") or {}).get("five_year_total"),
        "cross_cloud_gib_month": (estimate.get("network") or {}).get("cross_cloud_aws_gcp_gib_per_month"),
    }


def recommendation_table(estimates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [recommendation_row(e) for e in estimates]


def to_json(estimates: list[dict[str, Any]]) -> str:
    payload = {
        "report": "ecs_gcp_capacity_benchmark",
        "profiles": [e["profile"]["key"] for e in estimates],
        "estimates": estimates,
        "recommendation_table": recommendation_table(estimates),
    }
    return json.dumps(payload, indent=2, default=str)


def to_csv(estimates: list[dict[str, Any]]) -> str:
    rows = recommendation_table(estimates)
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def _md_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    """Render a Markdown table. ``columns`` is [(key, header), ...]."""
    header = "| " + " | ".join(h for _, h in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(k, "")) for k, _ in columns) + " |")
    return "\n".join(lines)


def to_markdown(estimates: list[dict[str, Any]]) -> str:
    rows = recommendation_table(estimates)
    parts: list[str] = []
    parts.append("# ECS GCP Capacity Sizing Report\n")
    parts.append(
        "> **Provenance:** ESTIMATE — documented per-unit assumptions × scenario "
        "profile (see `benchmarks/capacity/sizing.py::SizingConstants`). Not a "
        "measurement. Calibrate constants from a real benchmark run before "
        "committing to spend. See "
        "[`docs/benchmarking/GCP_CAPACITY_BENCHMARK_GUIDE.md`](../../docs/benchmarking/GCP_CAPACITY_BENCHMARK_GUIDE.md).\n"
    )

    # Recommendation table (headline).
    parts.append("## Recommendation summary\n")
    parts.append(_md_table(rows, [
        ("profile", "Profile"), ("apps", "Apps"),
        ("replicas", "Replicas"), ("gke_nodes", "GKE nodes"),
        ("gke_node_type", "Node type"),
        ("cloud_sql_tier", "Cloud SQL"), ("cloud_sql_storage_gib", "SQL GiB"),
        ("gcs_year1_gib", "GCS y1 GiB"), ("gcs_year5_gib", "GCS y5 GiB"),
        ("logs_per_day_gib", "Logs/day GiB"),
    ]))
    parts.append("")

    # Per-profile detail.
    for e in estimates:
        p = e["profile"]
        gke = e["gke_compute"]
        pg = e["postgres_pgvector"]
        gcs = e["gcs_object_storage"]
        logs = e["logging_monitoring"]
        parts.append(f"## {p['name']} (`{p['key']}`)\n")
        parts.append(f"_{p['description']}_\n")
        parts.append(
            f"- **Scale:** {p['apps']} apps · {p['frameworks']} frameworks · "
            f"{p['total_controls']} controls · {p['total_evidences']} evidences · "
            f"retention {p['retention_years']}y\n"
            f"- **Daily activity:** {p['api_requests_per_day']:,} API req · "
            f"{p['connector_runs_per_day']:,} connector runs · "
            f"{p['prompt_runs_per_day']:,} prompt runs · "
            f"{p['scheduler_jobs_per_day']:,} scheduler jobs\n"
        )
        parts.append("**GKE compute**\n")
        parts.append(
            f"- Peak ~{gke['peak_cores']} cores, ~{gke['peak_ram_mib']} MiB RAM (peak).\n"
            f"- Pod requests: {gke['recommended_pod']['cpu_request']} CPU / "
            f"{gke['recommended_pod']['memory_request']} RAM "
            f"(limits {gke['recommended_pod']['cpu_limit']} / "
            f"{gke['recommended_pod']['memory_limit']}).\n"
            f"- **{gke['recommended_replicas']} replicas** on "
            f"**{e['node_pool']['recommended_nodes']} × {e['node_pool']['node_machine_type']}** nodes.\n"
        )
        parts.append("**PostgreSQL / pgvector**\n")
        parts.append(
            f"- Year 1 ≈ {pg['storage_gib']['year_1_total']} GiB, "
            f"Year {p['retention_years']} ≈ {pg['storage_gib']['year_5_total']} GiB "
            f"(vectors now {pg['storage_gib']['vectors_current']} GiB).\n"
            f"- Recommended Cloud SQL: **{pg['recommended_cloud_sql']['tier']}** "
            f"({pg['recommended_cloud_sql']['vcpu']} vCPU / "
            f"{pg['recommended_cloud_sql']['ram_gib']} GiB, "
            f"{pg['recommended_cloud_sql']['storage_gib']} GiB, "
            f"{pg['recommended_cloud_sql']['ha']}).\n"
        )
        parts.append("**GCS object storage**\n")
        parts.append(
            f"- Year 1 ≈ {gcs['year_1_total_gib']} GiB, "
            f"Year {p['retention_years']} ≈ {gcs['year_5_total_gib']} GiB.\n"
        )
        parts.append("**Logging (Cloud Logging)**\n")
        parts.append(
            f"- ~{logs['per_day_gib']['total']} GiB/day, "
            f"~{logs['per_year_gib']} GiB/year.\n"
        )
        parts.append("")

    return "\n".join(parts)


def executive_summary(estimates: list[dict[str, Any]]) -> str:
    """A concise executive summary across profiles (Markdown)."""
    rows = recommendation_table(estimates)
    lines = ["# ECS Infrastructure — Executive Summary\n",
             "> Estimates from documented assumptions × scenario profiles. Not a "
             "measurement; calibrate before spend.\n",
             "| Profile | Apps | GKE (replicas×nodes) | Cloud SQL | GCS y1 | GCS y5 | Cost/mo | Cost 5y |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {r['name']} | {r['apps']} | {r['replicas']}×{r['gke_nodes']} "
            f"{r['gke_node_type']} | {r['cloud_sql_tier']} | {r['gcs_year1_gib']} GiB | "
            f"{r['gcs_year5_gib']} GiB | {r.get('cost_monthly')} | {r.get('cost_5yr')} |")
    lines.append("\n_Cost figures are illustrative (default GCP-like rates); replace "
                 "with a current quote._")
    return "\n".join(lines)


def _section_markdown(estimates: list[dict[str, Any]], title: str,
                      fn) -> str:
    """Generic per-profile section report. ``fn(estimate) -> markdown_body``."""
    parts = [f"# ECS {title}\n",
             "> Estimate (documented assumptions × profile). Not a measurement.\n"]
    for e in estimates:
        p = e["profile"]
        parts.append(f"## {p['name']} (`{p['key']}`)\n")
        parts.append(fn(e))
        parts.append("")
    return "\n".join(parts)


def cpu_report(estimates: list[dict[str, Any]]) -> str:
    def body(e):
        cpu = e.get("cpu_breakdown", {})
        ops = cpu.get("per_operation_core_hours_per_day", {})
        top = sorted(ops.items(), key=lambda kv: kv[1], reverse=True)[:10]
        rows = "\n".join(f"| {k} | {v} |" for k, v in top)
        return (f"- Peak ~{cpu.get('peak_cores')} cores; "
                f"{cpu.get('total_core_hours_per_day')} core-hours/day.\n\n"
                f"| Top operation (by core-hours/day) | core-hours/day |\n| --- | --- |\n{rows}\n")
    return _section_markdown(estimates, "CPU Benchmark Report", body)


def ram_report(estimates: list[dict[str, Any]]) -> str:
    def body(e):
        ram = e.get("ram_breakdown", {})
        cons = ram.get("per_consumer_peak_mib", {})
        rows = "\n".join(f"| {k} | {v} |" for k, v in cons.items())
        return (f"- Peak ~{ram.get('peak_total_gib')} GiB "
                f"(high-water ~{ram.get('high_water_mark_mib')} MiB).\n\n"
                f"| Consumer | peak MiB |\n| --- | --- |\n{rows}\n")
    return _section_markdown(estimates, "RAM Benchmark Report", body)


def storage_report(estimates: list[dict[str, Any]]) -> str:
    def body(e):
        gcs = e.get("gcs_object_storage", {})
        det = e.get("object_storage_detail", {})
        ret = det.get("retention_projection_gib", {})
        eff = det.get("efficiency", {})
        rows = "\n".join(f"| {k} | {v} |" for k, v in ret.items())
        return (f"- Year 1 ≈ {gcs.get('year_1_total_gib')} GiB; after dedup+compression ≈ "
                f"{eff.get('after_dedup_and_compression_gib')} GiB.\n\n"
                f"| Retention | GiB |\n| --- | --- |\n{rows}\n")
    return _section_markdown(estimates, "Object Storage Benchmark Report", body)


def database_report(estimates: list[dict[str, Any]]) -> str:
    def body(e):
        pg = e.get("postgres_pgvector", {})
        dur = e.get("db_durability", {})
        sql = pg.get("recommended_cloud_sql", {})
        return (f"- Cloud SQL: **{sql.get('tier')}** ({sql.get('vcpu')} vCPU / "
                f"{sql.get('ram_gib')} GiB, {sql.get('storage_gib')} GiB, {sql.get('ha')}).\n"
                f"- Year 1 ≈ {pg['storage_gib']['year_1_total']} GiB, "
                f"Year {e['profile']['retention_years']} ≈ {pg['storage_gib']['year_5_total']} GiB.\n"
                f"- WAL ~{dur.get('wal_gib_per_day')} GiB/day; full backup ≈ "
                f"{dur.get('backup', {}).get('full_backup_gib')} GiB; "
                f"restore working ≈ {dur.get('backup', {}).get('restore_working_gib')} GiB.\n"
                f"- Partitioning: {dur.get('partitioning', {}).get('strategy')}.\n")
    return _section_markdown(estimates, "Database Benchmark Report", body)


def network_report(estimates: list[dict[str, Any]]) -> str:
    def body(e):
        net = e.get("network", {})
        return (f"- Connector ingress ≈ {net.get('connector_ingress_gib_per_day')} GiB/day.\n"
                f"- **AWS↔GCP cross-cloud** ≈ {net.get('cross_cloud_aws_gcp_gib_per_day')} GiB/day "
                f"({net.get('cross_cloud_aws_gcp_gib_per_month')} GiB/month).\n"
                f"- Evidence upload/download ≈ {net.get('evidence_upload_gib_per_day')} / "
                f"{net.get('evidence_download_gib_per_day')} GiB/day.\n"
                f"- Total egress ≈ {net.get('total_egress_estimate_gib_per_month')} GiB/month.\n")
    return _section_markdown(estimates, "Network Benchmark Report", body)


def cost_report(estimates: list[dict[str, Any]]) -> str:
    def body(e):
        cost = e.get("cost", {})
        mb = cost.get("monthly_breakdown", {})
        rows = "\n".join(f"| {k} | {v} |" for k, v in mb.items())
        return (f"- Monthly total ≈ {cost.get('monthly_total')} {cost.get('currency')}; "
                f"annual ≈ {cost.get('annual_total')}; 5-year ≈ {cost.get('five_year_total')}.\n\n"
                f"| Component | monthly |\n| --- | --- |\n{rows}\n\n"
                f"> {cost.get('_disclaimer', '')}\n")
    return _section_markdown(estimates, "Cost Report", body)


#: Section report generators, keyed by CLI section name.
SECTION_REPORTS = {
    "cpu": cpu_report,
    "ram": ram_report,
    "storage": storage_report,
    "database": database_report,
    "network": network_report,
    "cost": cost_report,
    "executive": executive_summary,
}


def write_reports(estimates: list[dict[str, Any]], out_dir: str, *,
                  basename: str = "capacity", sections: bool = True) -> dict[str, str]:
    """Write JSON + Markdown + CSV to ``out_dir``; return the written paths."""
    import os

    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "json": os.path.join(out_dir, f"{basename}.json"),
        "markdown": os.path.join(out_dir, f"{basename}.md"),
        "csv": os.path.join(out_dir, f"{basename}.csv"),
    }
    with open(paths["json"], "w", encoding="utf-8") as fh:
        fh.write(to_json(estimates))
    with open(paths["markdown"], "w", encoding="utf-8") as fh:
        fh.write(to_markdown(estimates))
    with open(paths["csv"], "w", encoding="utf-8") as fh:
        fh.write(to_csv(estimates))
    if sections:
        for name, gen in SECTION_REPORTS.items():
            path = os.path.join(out_dir, f"{basename}_{name}.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(gen(estimates))
            paths[name] = path
    return paths
