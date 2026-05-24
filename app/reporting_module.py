"""Automated regulatory reporting simulation."""

from app import ecs_state
from app.analytics_module import enterprise_dashboard


def list_reports():
    stats = ecs_state.build_evidence_analytics()
    return [
        {
            "id": "rbi-cyber",
            "title": "RBI Cyber Security Compliance Summary",
            "format": "PDF",
            "frameworks": list(ecs_state.frameworks.keys())[:3],
        },
        {
            "id": "pci-audit",
            "title": "PCI DSS Audit-Ready Export",
            "format": "Excel",
            "frameworks": ["PCI DSS"],
        },
        {
            "id": "pan-india",
            "title": "Pan India Enterprise Compliance Report",
            "format": "PDF",
            "frameworks": list(ecs_state.frameworks.keys()),
        },
        {
            "id": "framework-summary",
            "title": "Framework Coverage Summary",
            "format": "Excel",
            "frameworks": list(ecs_state.frameworks.keys()),
        },
    ]


def generate_report_content(report_id: str) -> str:
    ent = enterprise_dashboard()
    stats = ent["analytics"]
    lines = [
        "ECS REGULATORY REPORT (DEMO EXPORT)",
        f"Report ID: {report_id}",
        "=" * 60,
        f"Enterprise Compliance: {stats['overall_compliance_pct']}%",
        f"Approved: {stats['totals']['approved']} / {stats['totals']['total']}",
        f"Pending: {stats['totals']['pending']}",
        f"Rejected: {stats['totals']['rejected']}",
        "",
        "Framework Summary:",
    ]
    for fw in stats["framework_stats"]:
        lines.append(
            f"  - {fw['name']}: {fw['compliance_pct']}% ({fw['approved']}/{fw['total']} approved)"
        )
    lines.append("")
    lines.append("Pan India National Score: {}%".format(ent["national_score"]))
    for r in ent["regions"]:
        lines.append(f"  - {r['region']}: {r['score']}% ({r['branches']} branches)")
    lines.append("")
    lines.append("End of audit-ready export.")
    return "\n".join(lines)
