#!/usr/bin/env python3
"""Seed realistic enterprise governance data on top of the evidence repository.

Run inside the ecs container (so ECS_REPO_PG_* env points at the postgres service):

    docker compose exec ecs python demo-data/seed_governance.py

Idempotent: safe to run repeatedly. It:
  1. ensures the governance schema exists,
  2. seeds the control catalog (covered controls + intentional gaps),
  3. registers applications derived from collected evidence + a few portfolio apps,
  4. assigns frameworks in scope per application,
  5. seeds the evidence review lifecycle (Approved / UnderReview / Rejected / Expired),
  6. seeds recurring collection schedules.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from ecs_platform.governance import init_governance_schema, onboard_application, upsert_schedule
from ecs_platform.repository import EvidenceRepository

NOW = datetime.now(timezone.utc)

# control_id -> (name, domain, framework_code). The first 6 are produced by the
# seeded connectors (covered); the rest are deliberate gaps for realism.
CATALOG = {
    "change-management":       ("Change Management", "SDLC", "SOC2"),
    "code-review":             ("Peer Code Review", "SDLC", "SOC2"),
    "ci-cd":                   ("CI/CD Pipeline Controls", "SDLC", "SOC2"),
    "vulnerability-management":("Vulnerability Management", "Security", "SOC2"),
    "secure-sdlc":             ("Secure SDLC", "SDLC", "ISO27001"),
    "code-quality":            ("Code Quality Gate", "SDLC", "ISO27001"),
    # --- intentional gaps (no evidence yet) ---
    "access-review":           ("Periodic Access Review", "Access Control", "SOC2"),
    "vendor-risk":             ("Third-Party / Vendor Risk", "Third Party", "SOC2"),
    "incident-response":       ("Incident Response", "Security Ops", "ISO27001"),
    "logging-monitoring":      ("Logging & Monitoring", "Security Ops", "ISO27001"),
    "data-encryption":         ("Data Encryption at Rest/Transit", "Cryptography", "PCI-DSS"),
    "network-segmentation":    ("Network Segmentation", "Network", "PCI-DSS"),
    "bcp-dr":                  ("Business Continuity / DR", "Resilience", "RBI-CSF"),
    "backup-recovery":         ("Backup & Recovery", "Resilience", "RBI-CSF"),
}

# realistic metadata keyed by a normalized application token.
APP_META = {
    "mobile":   {"bu": "Retail Banking", "owner": "Priya Sharma", "crit": "Critical", "stack": "Kotlin, Swift, Spring Boot"},
    "net":      {"bu": "Retail Banking", "owner": "Arjun Mehta", "crit": "Critical", "stack": "React, Java, PostgreSQL"},
    "upi":      {"bu": "Payments", "owner": "Sneha Iyer", "crit": "Critical", "stack": "Go, Kafka, Redis"},
    "payment":  {"bu": "Payments", "owner": "Rahul Verma", "crit": "Critical", "stack": "Java, Oracle"},
    "treasury": {"bu": "Wholesale Banking", "owner": "Anita Desai", "crit": "High", "stack": "Python, PostgreSQL"},
    "api":      {"bu": "Platform", "owner": "Vikram Nair", "crit": "High", "stack": "Go, Envoy, Kubernetes"},
}
DEFAULT_FRAMEWORKS = ["SOC2", "ISO27001"]
CRITICAL_FRAMEWORKS = ["SOC2", "ISO27001", "PCI-DSS", "RBI-CSF"]

# Extra portfolio applications with no evidence yet (onboarding / decommissioned).
EXTRA_APPS = [
    {"name": "Customer Data Lake", "business_unit": "Data & Analytics", "owner": "Meera Kapoor",
     "criticality": "High", "environment": "Production", "lifecycle_status": "Onboarding",
     "tech_stack": "Spark, Delta Lake", "frameworks": "SOC2, ISO27001, RBI-CSF"},
    {"name": "Branch Locator", "business_unit": "Retail Banking", "owner": "Sanjay Gupta",
     "criticality": "Low", "environment": "Production", "lifecycle_status": "Active",
     "tech_stack": "Node.js", "frameworks": "SOC2"},
    {"name": "Legacy Loan Origination", "business_unit": "Wholesale Banking", "owner": "Deepa Rao",
     "criticality": "Medium", "environment": "Production", "lifecycle_status": "Decommissioned",
     "tech_stack": "Java EE", "frameworks": "SOC2, ISO27001"},
]


def _meta_for(app: str) -> dict:
    low = app.lower()
    for tok, m in APP_META.items():
        if tok in low:
            return m
    return {"bu": "Engineering", "owner": "Platform Team", "crit": "Medium", "stack": "—"}


def _bucket(uid: str) -> int:
    return int(hashlib.sha256(uid.encode()).hexdigest(), 16) % 100


def seed() -> None:
    s = init_governance_schema()
    if not s.get("ok"):
        print(f"[FAIL] governance schema: {s.get('error')}")
        return
    print("[ok] governance schema ready")

    repo = EvidenceRepository()
    repo.connect()
    cur = repo.connect().cursor()

    # 1. control catalog
    for cid, (name, domain, fw) in CATALOG.items():
        cur.execute(
            "INSERT INTO control_catalog (control_id, name, domain, framework_code) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (control_id) DO UPDATE SET name=EXCLUDED.name, domain=EXCLUDED.domain, "
            "framework_code=EXCLUDED.framework_code", (cid, name, domain, fw))
    print(f"[ok] control catalog: {len(CATALOG)} controls")

    # 2. applications derived from evidence
    cur.execute("SELECT DISTINCT application FROM evidence WHERE application <> '' ORDER BY 1")
    apps = [r[0] for r in cur.fetchall()]
    for app in apps:
        m = _meta_for(app)
        fws = CRITICAL_FRAMEWORKS if m["crit"] == "Critical" else DEFAULT_FRAMEWORKS
        onboard_application({
            "slug": app, "name": app.replace("-", " ").title(),
            "description": f"{m['bu']} application onboarded into ECS.",
            "owner": m["owner"], "owner_email": f"{m['owner'].split()[0].lower()}@bank.example",
            "business_unit": m["bu"], "criticality": m["crit"], "environment": "Production",
            "lifecycle_status": "Active", "tech_stack": m["stack"], "hosting": "AWS ap-south-1",
            "frameworks": fws,
        }, actor="seed", role="system")
    print(f"[ok] applications from evidence: {len(apps)} ({', '.join(apps) or 'none'})")

    # 2b. extra portfolio apps
    for a in EXTRA_APPS:
        onboard_application(a, actor="seed", role="system")
    print(f"[ok] extra portfolio applications: {len(EXTRA_APPS)}")

    # 3. evidence review lifecycle
    cur.execute("SELECT evidence_uid FROM evidence ORDER BY id")
    uids = [r[0] for r in cur.fetchall()]
    dist = {"Approved": 0, "UnderReview": 0, "Rejected": 0, "Expired": 0, "Collected": 0}
    for uid in uids:
        b = _bucket(uid)
        if b < 65:
            status, valid_until, reviewer = "Approved", NOW + timedelta(days=90), "Auditor"
        elif b < 80:
            status, valid_until, reviewer = "UnderReview", None, "Auditor"
        elif b < 88:
            status, valid_until, reviewer = "Rejected", None, "Auditor"
        elif b < 95:
            status, valid_until, reviewer = "Expired", NOW - timedelta(days=10), "System"
        else:
            status, valid_until, reviewer = "Collected", None, None
        dist[status] += 1
        cur.execute(
            """
            INSERT INTO evidence_reviews (evidence_uid, status, reviewer, note, reviewed_at, valid_until)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (evidence_uid) DO UPDATE SET status=EXCLUDED.status, reviewer=EXCLUDED.reviewer,
                reviewed_at=EXCLUDED.reviewed_at, valid_until=EXCLUDED.valid_until, updated_at=now()
            """,
            (uid, status, reviewer, f"Seeded {status}",
             NOW if status != "Collected" else None, valid_until))
    print(f"[ok] evidence reviews: {len(uids)} -> {dist}")

    # 4. schedules (clear + reseed to stay idempotent)
    cur.execute("DELETE FROM collection_schedules WHERE owner = 'seed'")
    schedules = [
        ("Daily Gitea commit sync", "gitea", "", "Daily"),
        ("Daily Jenkins build sync", "jenkins", "", "Daily"),
        ("Weekly SonarQube scan sync", "sonarqube", "", "Weekly"),
        ("Monthly GitHub release sync", "github", "", "Monthly"),
        ("Daily Jira change sync", "jira", "", "Daily"),
    ]
    freq_h = {"Hourly": 1, "Daily": 24, "Weekly": 168, "Monthly": 720}
    for i, (name, conn, app_slug, freq) in enumerate(schedules):
        # stagger: make the first two already due
        last = NOW - timedelta(hours=freq_h[freq] + (2 if i < 2 else -4))
        nxt = last + timedelta(hours=freq_h[freq])
        cur.execute(
            "INSERT INTO collection_schedules (name, connector, app_slug, frequency, owner, enabled, "
            "last_run, last_status, next_run) VALUES (%s,%s,%s,%s,'seed',TRUE,%s,'OK',%s)",
            (name, conn, app_slug, freq, last, nxt))
    print(f"[ok] schedules: {len(schedules)}")

    repo.record_audit("seed", "governance.seed", role="system", resource="governance",
                      detail={"controls": len(CATALOG), "apps": len(apps) + len(EXTRA_APPS),
                              "reviews": len(uids)})
    repo.close()
    print("[done] governance seed complete")


if __name__ == "__main__":
    seed()
