# ECS Leadership Demo Script (CIO / EVP / MD)

A presenter's script for a **5-minute executive walkthrough** of ECS (Evidence
Collection System). Audience: senior leadership (CIO, EVP, MD, Head of Audit /
Compliance). This is the *what to say and what to click* script; the hands-on
operator steps live in [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md).

> Everything here runs **offline** — no bank systems, no live network, no
> production data. Nothing shown contains real IPs, hostnames, or secrets.

---

## 0. Before they walk in (2 minutes, presenter only)

```bash
export DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py     # expect: 10/10 ALL PASS
PYTHONPATH=. uvicorn app.main:app --port 8000         # start the UI
```

Confirm the smoke runner prints **`10/10 checks passed -> ALL PASS`**. It walks
the entire platform end-to-end and is your safety net: if it's green, the live
demo will be green. Have the browser open at `http://127.0.0.1:8000/mvp/audit/dashboard`.

---

## 1. The one-sentence pitch (say this first)

> "ECS automatically **collects audit evidence** from our technology estate, maps
> it to the frameworks our regulators care about, and tells us — with proof — how
> **audit-ready** we are, continuously, instead of scrambling before each audit."

Then the value in one breath:
> "It turns a **manual, weeks-long, screenshot-driven** evidence exercise into a
> **repeatable, defensible, on-demand** one."

---

## 2. Explain ECS in 5 minutes (the story arc)

Draw or point at this single line — it is the whole platform:

```
Technology  ->  Predefined Queries (Controls)  ->  Frameworks  ->  Evidence  ->  Validation  ->  Observations  ->  Audit-Ready Packs
```

Talking points (one sentence each):
1. **Coverage** — "167 curated, **read-only** checks across 20 technologies
   (Oracle, PostgreSQL, SQL Server, Mongo, Redis, Linux/RHEL, NGINX, Apache,
   Tomcat, Kubernetes, OpenShift…) mapped to 16 frameworks (RBI, PCI DSS, ISO
   27001, ITPP…)."
2. **Discovery** — "ECS discovers assets and **fingerprints** their technology, so
   it knows which controls apply to what."
3. **Evidence** — "It runs the applicable checks and captures the result as
   **evidence with a hash** — tamper-evident, versioned, no credentials stored."
4. **Judgement** — "It **validates** each piece of evidence deterministically
   (Pass / Fail / Warning) and raises **observations** for anything non-compliant."
5. **Audit pack** — "It assembles **audit-ready evidence packs** with a verifiable
   manifest an auditor can trust."
6. **Readiness** — "All of it rolls up into an **executive readiness dashboard**."

---

## 3. What to click (the 90-second UI tour)

Open these pages in order and say the one-liner:

| # | Click | Say |
|---|-------|-----|
| 1 | `/mvp/audit/dashboard` | "Executive readiness at a glance — coverage, open observations, risk band." |
| 2 | `/mvp/audit/assets` | "The estate ECS discovered and fingerprinted." |
| 3 | `/mvp/audit/technology-mapping` | "Every technology → control → framework mapping. This is our audit scope, computed." |
| 4 | `/mvp/audit/evidence-runs` | "An evidence collection run — each control, its status, the captured evidence." |
| 5 | `/mvp/audit/validation-results` | "The deterministic verdicts — Compliant / Non-Compliant, with rationale." |
| 6 | `/mvp/audit/observations` | "Findings raised automatically from failures, with severity and remediation." |
| 7 | `/mvp/audit/evidence-packs` | "One click assembles an auditor-ready pack with a verifiable hash." |
| 8 | `/mvp/audit/executive-readiness` | "Back to the story: are we audit-ready? Here's the evidence." |

> Every page is read-only and loads instantly from the in-memory demo state. If a
> page looks empty, run the smoke runner once more — it seeds a representative run.

---

## 4. How to explain the audit value (for the Head of Audit / MD)

- **Defensibility** — "Every result is captured with a **SHA-256 content hash** and
  a versioned history. Packs carry a **verifiable manifest** — an auditor can
  recompute the hash and confirm nothing was altered."
- **Repeatability** — "The same run can be re-executed on demand; evidence is
  **re-versioned**, not overwritten, so we keep a full timeline."
- **Coverage-to-framework line of sight** — "We can show, per framework, exactly
  which controls are covered and where the gaps are — **before** the auditor asks."
- **Least privilege & safety** — "All checks are **read-only**; ECS stores
  **metadata and hashes, never secrets or raw credentials**."
- **Separation from GRC** — "ECS is the **evidence engine**; it complements (does
  not replace) our GRC/workflow tooling."

---

## 5. How to explain UAT readiness (for the CIO / EVP)

- "The platform is **environment-driven**: the same code runs against local demo
  containers today and against **bank UAT endpoints** by setting environment
  variables — **no code change**."
- "Connectors and 11 enterprise integrations (ServiceNow, Archer, SharePoint/Teams/
  Outlook via Microsoft Graph, Jira, Confluence, SonarQube, Checkmarx, Prisma Cloud,
  Tripwire) are **config-driven**; secrets come from a **secret store**, never from Git."
- "We have a **Bank Developer UAT Checklist** (VPN, DNS, ports, read-only service
  accounts, secrets outside Git, diagnostics, smoke, evidence review) — see
  [UAT_INTEGRATION_GUIDE.md](UAT_INTEGRATION_GUIDE.md)."
- "What's left for production is **operational, not architectural** — durable
  Postgres persistence, real credentials, live UAT validation, HA/monitoring —
  all tracked openly in the
  [PRODUCTION_READINESS_GAP_REGISTER.md](PRODUCTION_READINESS_GAP_REGISTER.md).
  This is a professional readiness register, not a list of surprises."

---

## 6. Likely questions (have these ready)

| They ask | You say |
|----------|---------|
| "Is this touching production data now?" | "No — this is offline demo state. Production is opt-in via environment config, with read-only accounts." |
| "Where do the credentials live?" | "In a secret store / `.env.uat`, never in Git. ECS only ever displays SET/MISSING." |
| "Can auditors trust the evidence?" | "Yes — hashed, versioned, with a verifiable pack manifest." |
| "What's the gap to production?" | "Durable persistence, real creds, live UAT, HA/monitoring — all in the gap register, all operational." |
| "How much is automated vs manual?" | "Discovery, collection, validation, observation, packaging, and dashboards are automated; humans review and sign off." |

---

## 7. Close (say this last)

> "ECS gives us **continuous, provable audit readiness** across the estate — the
> foundation is built and validated end-to-end offline today; the remaining work
> is wiring it to our UAT/production environments, which is configuration and
> operations, not redesign."

---

## Appendix — one-command proof

If you can only do one thing, run this and show the output:

```bash
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py
```

It exercises: **catalog loaded → technologies detected → controls mapped → mocked
run executed → validation completed → observation generated → evidence pack
generated → dashboard summary produced → integration adapters checked → final
PASS/FAIL**, offline, in under a second.
