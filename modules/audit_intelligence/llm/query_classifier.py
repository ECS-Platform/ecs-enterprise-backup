"""Deterministic audit-query classifier + entity extractor (no LLM, no network).

Classifies a natural-language audit query into ``deterministic`` /
``llm_assisted`` / ``hybrid`` / ``unsupported`` using keyword heuristics, and
extracts entities (application, framework, severity, date range, status, owner,
technology, control, region, phase). This mirrors the ECS
deterministic-vs-LLM-assisted policy so the router can decide DB-first vs
LLM-assisted answering.

Deterministic wins for pure "count/how many/list/which are older than" questions;
predictive/analytical verbs (likely, chance, predict, forecast, root cause) mark
llm_assisted; a mix marks hybrid.
"""

from __future__ import annotations

import re
from typing import Any

# --------------------------------------------------------------------------- #
# Keyword signals
# --------------------------------------------------------------------------- #
_DETERMINISTIC_SIGNALS = (
    "how many", "count", "number of", "list", "which observations are older",
    "older than", "overdue", "till date", "to date", "how much",
    "which framework has the highest", "highest number", "least audit-ready",
    "which applications have", "status of",
)
_DETAIL_SIGNALS = (
    "detail", "details", "describe", "description", "root cause", "impact",
    "recommendation", "finding",
)
_EVIDENCE_RAG_SIGNALS = (
    "what evidence", "which evidence", "evidence supports", "supports encryption",
    "evidence for", "physical evidence", "from the evidence", "evidence file",
    "summarize evidence", "evidence summary", "evidence gap", "gap identification",
    "map to control", "map evidence", "evidence to control", "evidence-to-control",
    "recommend control from evidence", "control mapping from evidence",
    "cite the evidence",
)
_LLM_SIGNALS = (
    "chance", "chances", "likelihood", "likely", "predict", "prediction",
    "forecast", "probability", "root cause", "root causes", "why", "explain",
    "recommend", "recommendation", "next best action", "draft", "justification",
    "may remain", "will not be raised", "escalation", "expected to", "assess",
)
_SUMMARY_SIGNALS = (
    "summarize", "summary", "summarise", "generate", "executive", "board",
    "briefing", "compare", "comparison", "overview", "checklist", "notes",
)

# --------------------------------------------------------------------------- #
# Entity vocabularies (demo-safe; no secrets/IPs)
# --------------------------------------------------------------------------- #
_APPLICATIONS = (
    "Net Banking", "Mobile Banking", "Payments", "UPI", "Treasury",
    "Card Platform", "Corporate Banking", "Trade Finance", "Wealth Management",
    "Loan Origination",
)
_FRAMEWORKS = (
    "C-SITE", "CSITE", "PCI DSS", "PCI-DSS", "RBI Cyber Security", "RBI", "ISO27001",
    "ISO 27001", "SOC2", "SOC 2", "ITPP", "DPSC", "NIST",
)
_SEVERITIES = ("Critical", "High", "Medium", "Low", "Informational")
_STATUSES = ("Draft", "Submitted", "Approved", "Rejected", "Remediated", "Closed",
             "Open", "Overdue", "Pending")
_TECHNOLOGIES = (
    "PostgreSQL", "Oracle", "SQL Server", "MongoDB", "Redis", "Aerospike",
    "NGINX", "Apache", "Tomcat", "Kubernetes", "OpenShift", "Linux",
)
_REGIONS = ("Pan India", "Pan-India", "North", "South", "East", "West", "National")
_PHASES = ("Draft", "Submission", "Review", "Approval", "Remediation", "Closure")

_DATE_RE = re.compile(
    r"\b(\d+\s*(?:day|days|week|weeks|month|months|year|years))\b"
    r"|\b(this year|last year|this quarter|quarter end|ytd|q[1-4])\b",
    re.IGNORECASE,
)
_OWNER_RE = re.compile(r"\bowner[s]?\b|\bapp[- ]?owner[s]?\b", re.IGNORECASE)
_CONTROL_RE = re.compile(r"\b([A-Z]{2,6}-\d{2,4})\b")  # e.g. NGX-003, ASX-001


def _find_first(text_lower: str, vocab: tuple[str, ...]) -> str:
    for term in vocab:
        if term.lower() in text_lower:
            return term
    return ""


def _find_all(text_lower: str, vocab: tuple[str, ...]) -> list[str]:
    return [term for term in vocab if term.lower() in text_lower]


def extract_entities(query: str) -> dict[str, Any]:
    """Extract audit entities from a free-form query (best-effort, deterministic)."""
    q = (query or "").strip()
    low = q.lower()

    date_match = _DATE_RE.search(q)
    date_range = ""
    if date_match:
        date_range = next((g for g in date_match.groups() if g), "")

    controls = _CONTROL_RE.findall(q)

    return {
        "application": _find_first(low, _APPLICATIONS),
        "applications": _find_all(low, _APPLICATIONS),
        "framework": _find_first(low, _FRAMEWORKS),
        "frameworks": _find_all(low, _FRAMEWORKS),
        "severity": _find_first(low, _SEVERITIES),
        "status": _find_first(low, _STATUSES),
        "technology": _find_first(low, _TECHNOLOGIES),
        "region": _find_first(low, _REGIONS),
        "phase": _find_first(low, _PHASES),
        "owner": bool(_OWNER_RE.search(q)),
        "control": controls[0] if controls else "",
        "controls": controls,
        "date_range": date_range,
    }


def resolve_answer_mode(query: str, query_type: str = "") -> str:
    """Map a query to deterministic | rag | hybrid answer mode for the workbench."""
    low = (query or "").strip().lower()
    det = [s for s in _DETERMINISTIC_SIGNALS if s in low]
    details = [s for s in _DETAIL_SIGNALS if s in low]
    evidence = [s for s in _EVIDENCE_RAG_SIGNALS if s in low]
    if evidence and not det:
        return "rag"
    if det and (details or evidence):
        return "hybrid"
    if det and not details and not evidence:
        return "deterministic"
    if query_type == "deterministic":
        return "deterministic"
    if evidence:
        return "rag"
    if query_type in ("hybrid", "llm_assisted"):
        return "hybrid"
    return "hybrid" if (details or evidence) else (query_type or "hybrid")


def classify(query: str) -> dict[str, Any]:
    """Classify a query as deterministic / llm_assisted / hybrid / unsupported.

    Returns ``{"query_type", "confidence", "signals", "entities", "reason",
    "answer_mode"}``.
    """
    q = (query or "").strip()
    low = q.lower()
    if not low:
        return {
            "query_type": "unsupported", "confidence": "low",
            "signals": {}, "entities": extract_entities(q),
            "reason": "empty query", "answer_mode": "unsupported",
        }

    det = [s for s in _DETERMINISTIC_SIGNALS if s in low]
    llm = [s for s in _LLM_SIGNALS if s in low]
    summ = [s for s in _SUMMARY_SIGNALS if s in low]
    details = [s for s in _DETAIL_SIGNALS if s in low]
    evidence = [s for s in _EVIDENCE_RAG_SIGNALS if s in low]

    entities = extract_entities(q)

    # Decision logic (deterministic policy):
    if evidence and not det:
        query_type, reason = "hybrid", "physical evidence / RAG question"
    elif det and details and not llm:
        query_type, reason = "hybrid", "deterministic count plus observation details"
    elif det and not llm and not summ and not details and not evidence:
        query_type, reason = "deterministic", "count/list/aging signals, no predictive/summary verbs"
    elif det and summ and not llm:
        query_type, reason = "hybrid", "deterministic count + summarization request"
    elif det and not llm:
        query_type, reason = "deterministic", "count/list/aging signals, no predictive verbs"
    elif llm and not det:
        if summ and not any(w in low for w in ("chance", "likelihood", "predict", "forecast",
                                               "probability", "root cause")):
            query_type, reason = "hybrid", "summarization of ECS data"
        else:
            query_type, reason = "llm_assisted", "predictive/analytical verbs present"
    elif det and llm:
        query_type, reason = "hybrid", "both deterministic and analytical signals"
    elif summ:
        query_type, reason = "hybrid", "summarization/report request over ECS data"
    else:
        has_entity = any(entities[k] for k in ("application", "framework", "severity",
                                               "status", "technology", "control"))
        if has_entity:
            query_type, reason = "hybrid", "entity-referencing question, default to grounded QA"
        else:
            query_type, reason = "unsupported", "no recognizable audit intent or entity"

    strength = len(det) + len(llm) + len(summ) + len(evidence) + len(details)
    confidence = "high" if strength >= 2 else ("medium" if strength == 1 else "low")
    answer_mode = resolve_answer_mode(q, query_type)

    return {
        "query_type": query_type,
        "confidence": confidence,
        "signals": {
            "deterministic": det,
            "llm_assisted": llm,
            "summary": summ,
            "details": details,
            "evidence_rag": evidence,
        },
        "entities": entities,
        "reason": reason,
        "answer_mode": answer_mode,
    }
