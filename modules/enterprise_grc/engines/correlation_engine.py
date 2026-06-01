"""Cross-tool governance correlation engine."""

from __future__ import annotations

from app import ecs_state


CORRELATION_CHAINS = [
    {
        "chain_id": "COR-001",
        "title": "ServiceNow P1 → Jira → Prisma → ECS Control Failure",
        "severity": "Critical",
        "status": "Open",
        "source_tool": "ServiceNow",
        "source_record": "INC0041287 — Net Banking login degradation",
        "links": [
            {"tool": "Jira", "record": "REM-8842 — Session cache fix", "status": "In Progress"},
            {"tool": "Prisma Cloud", "record": "CSPM-991 — Exposed Redis cache", "status": "Open"},
            {"tool": "ECS", "record": "PCI DSS — Req 10.6 Log Review", "status": "Control Failed Validation"},
            {"tool": "ECS TD", "record": "EXC-2026-014 — TLS exception", "status": "Active"},
        ],
        "application": "Net Banking",
        "framework": "PCI DSS",
    },
    {
        "chain_id": "COR-002",
        "title": "Tripwire Drift → OS Baselining → High-Risk App",
        "severity": "High",
        "status": "Open",
        "source_tool": "Tripwire",
        "source_record": "DRIFT-7721 — sudoers unauthorized change",
        "links": [
            {"tool": "ECS", "record": "OS Baselining — Privileged Command Logging", "status": "Rejected"},
            {"tool": "ECS Risk", "record": "RSK-2026-005 — OS baselining drift", "status": "Open"},
            {"tool": "Compensating Control", "record": "Enhanced SOC monitoring — 30d", "status": "Active"},
            {"tool": "CMDB", "record": "AST-SRV-001 — NETBANKING_PROD", "status": "Critical Asset"},
        ],
        "application": "Net Banking",
        "framework": "OS Baselining",
    },
    {
        "chain_id": "COR-003",
        "title": "SonarQube → AppSec → VAPT → Jira Remediation",
        "severity": "High",
        "status": "Open",
        "source_tool": "SonarQube",
        "source_record": "SAST-4421 — SQL injection in mobile API layer",
        "links": [
            {"tool": "Checkmarx", "record": "CX-9912 — OWASP A03 confirmation", "status": "Validated"},
            {"tool": "ECS", "record": "AppSec — SAST critical findings", "status": "Pending Review"},
            {"tool": "ECS", "record": "VAPT — API Penetration Testing", "status": "Open Finding"},
            {"tool": "Jira", "record": "SEC-2201 — Parameterized query fix", "status": "Sprint 24"},
        ],
        "application": "Mobile Banking",
        "framework": "AppSec",
    },
    {
        "chain_id": "COR-004",
        "title": "ServiceNow Change → ITPP CAB → Tripwire Validation",
        "severity": "Medium",
        "status": "Closed",
        "source_tool": "ServiceNow",
        "source_record": "CHG003892 — Firewall rule for DR test",
        "links": [
            {"tool": "ECS", "record": "ITPP — CAB Approval", "status": "Approved"},
            {"tool": "ECS", "record": "ITPP — Emergency Change Approval", "status": "PIR Complete"},
            {"tool": "Tripwire", "record": "No drift post-change", "status": "Validated"},
            {"tool": "SharePoint", "record": "CAB minutes Q2 uploaded", "status": "Evidence Linked"},
        ],
        "application": "Net Banking",
        "framework": "ITPP",
    },
    {
        "chain_id": "COR-005",
        "title": "Prisma IAM → CSITE → Cloud Risk Register",
        "severity": "High",
        "status": "Open",
        "source_tool": "Prisma Cloud",
        "source_record": "IAM-3381 — Over-privileged UPI service account",
        "links": [
            {"tool": "ECS", "record": "CSITE — Privileged Access Monitoring", "status": "High Risk"},
            {"tool": "ECS Risk", "record": "RSK-2026-004 — Cloud IAM excess privileges", "status": "Open"},
            {"tool": "Jira", "record": "CLOUD-551 — IAM role tightening", "status": "Backlog"},
            {"tool": "ServiceNow", "record": "PRB002104 — Repeat IAM pattern", "status": "Root Cause Analysis"},
        ],
        "application": "UPI",
        "framework": "CSITE",
    },
]


def build_correlation_dashboard(role: str = "owner") -> dict:
    open_chains = [c for c in CORRELATION_CHAINS if c["status"] == "Open"]
    return {
        "chains": CORRELATION_CHAINS,
        "kpis": [
            {"label": "Active Correlations", "value": len(open_chains), "tone": "primary"},
            {"label": "Critical Chains", "value": len([c for c in open_chains if c["severity"] == "Critical"]), "tone": "danger"},
            {"label": "Tools Integrated", "value": 9, "tone": "info"},
            {"label": "Closed This Month", "value": len([c for c in CORRELATION_CHAINS if c["status"] == "Closed"]), "tone": "success"},
        ],
        "by_tool": _tool_index(),
        "actions": ["view_chain", "escalate", "link_control", "open_source_record"],
        "role": role,
    }


def _tool_index() -> dict[str, int]:
    counts: dict[str, int] = {}
    for chain in CORRELATION_CHAINS:
        counts[chain["source_tool"]] = counts.get(chain["source_tool"], 0) + 1
        for link in chain["links"]:
            counts[link["tool"]] = counts.get(link["tool"], 0) + 1
    return counts


def find_correlations_by_tool(tool: str) -> list[dict]:
    tool_l = tool.lower()
    return [
        c for c in CORRELATION_CHAINS
        if tool_l in c["source_tool"].lower()
        or any(tool_l in l["tool"].lower() for l in c["links"])
    ]
