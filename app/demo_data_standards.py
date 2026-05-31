"""ECS Enterprise Demo Quality — shared mock data generators.

Deterministic, traceable datasets for leadership demos. Presentation layer only;
does not alter business logic in domain engines.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any, Callable


def seed(*parts: Any) -> int:
    return int(hashlib.md5("::".join(str(p) for p in parts).encode()).hexdigest(), 16)


def between(s: int, lo: int, hi: int) -> int:
    return lo + (s % max(hi - lo + 1, 1))


def pick(s: int, items: list) -> Any:
    return items[s % len(items)] if items else None


BANKING_OWNERS = [
    "R. Mehta", "A. Sharma", "K. Reddy", "S. Banerjee", "M. D'Souza",
    "P. Nair", "V. Desai", "S. Nair", "N. Iyer", "T. Kapoor",
    "L. Menon", "J. Patel", "H. Singh", "D. Bose", "R. Khanna",
]

BANKING_APPLICATIONS = [
    "Net Banking", "Mobile Banking", "Payments", "Treasury", "Customer Onboarding",
    "Core Banking", "Trade Finance", "Cards", "Wealth Management", "CRM",
    "ATM Switch", "UPI Gateway", "Loan Origination", "Fraud Monitoring", "Data Lake",
]

AUDIT_ACTIONS = [
    "Evidence Upload", "Evidence Approved", "Approval", "Exception Approved", "Exception Raised",
    "Observation Raised", "Observation Closed", "Closure", "VAPT", "UAT",
    "Model Approved", "Prompt Approved", "Control Mapping", "Framework Mapping",
    "Audit Closure", "Control Validated", "Gap Identified", "CAB Approval",
    "Risk Acceptance", "Policy Review", "Prompt Audit", "VAPT Finding Closed",
]

AUDIT_ACTORS = [
    "S. Nair (Auditor)", "V. Desai (Compliance)", "Internal Audit", "KPMG — PCI Audit",
    "EY VAPT", "AppSec CoE", "AI CoE", "Model Risk Board", "Compliance Head", "CIO",
]


def generate_audit_trail(
    count: int,
    anchor: date,
    *,
    years_back: int = 3,
    actions: list[str] | None = None,
    actors: list[str] | None = None,
    detail_builder: Callable[[int, str, str], str] | None = None,
) -> list[dict[str, str]]:
    """Generate *count* audit events spanning *years_back* years ending at *anchor*."""
    actions = actions or AUDIT_ACTIONS
    actors = actors or AUDIT_ACTORS
    start = anchor - timedelta(days=365 * years_back)
    span_days = (anchor - start).days or 1
    rows: list[dict[str, str]] = []
    for i in range(count):
        s = seed("audit", i)
        day_offset = between(s, 0, span_days)
        ts = start + timedelta(days=day_offset, hours=between(s >> 4, 8, 18), minutes=between(s >> 8, 0, 59))
        action = pick(s, actions)
        actor = pick(s >> 2, actors)
        if detail_builder:
            detail = detail_builder(i, action, actor)
        else:
            app = pick(s >> 6, BANKING_APPLICATIONS)
            fw = pick(s >> 10, ["PCI DSS", "DPSC", "AppSec", "VAPT", "AI Governance", "ITPP"])
            detail = f"{app} — {fw} — {action.lower()} record #{i + 1:04d}"
        rows.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M UTC"),
            "actor": actor,
            "action": action,
            "detail": detail,
        })
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    return rows


def generate_monthly_trend(
    months: int,
    anchor: date,
    *,
    prefix: str,
    value_fn: Callable[[int, int], int],
    label_fmt: str = "%b %Y",
) -> list[dict[str, Any]]:
    """Return *months* of trend points ending at *anchor* month."""
    points: list[dict[str, Any]] = []
    for i in range(months - 1, -1, -1):
        d = anchor.replace(day=1) - timedelta(days=28 * i)
        s = seed(prefix, d.year, d.month)
        points.append({
            "month": d.strftime(label_fmt),
            "month_key": d.strftime("%Y-%m"),
            "value": value_fn(s, i),
            "index": months - 1 - i,
        })
    return points


def expand_catalog(
    base: list[dict],
    target: int,
    builder: Callable[[int], dict],
) -> list[dict]:
    """Ensure at least *target* rows; preserve *base* items first."""
    out = list(base)
    n = len(out)
    while len(out) < target:
        out.append(builder(n))
        n += 1
    return out
