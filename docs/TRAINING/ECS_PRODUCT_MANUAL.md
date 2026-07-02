# ECS Product Manual (Knowledge Transfer)

**Audience:** new joiners, product managers, demo teams. **Goal:** understand *what ECS is, why it exists, and what it does* in one read. This is the training-grade product manual; the exhaustive reference is `docs/product_manual/ECS_PRODUCT_MANUAL.md`.

> **Canonical facts:** 15 frameworks · 305 controls · 702 evidence records · 12 connectors · 9 RBAC roles · ~79 screens across 7 navigation groups. (Demo mode seeds larger rounded datasets for presentation.)

---

## 1. What ECS is

**ECS (Evidence Collection System)** is an enterprise compliance and audit-evidence platform for regulated organizations (built around banking/RBI use cases). It automates the chain:

> **Framework → Control → Evidence → Validation → Audit → Reporting**

It connects to engineering and IT source systems, collects compliance evidence automatically, scores readiness continuously, lets evidence be **reused across many frameworks**, and produces regulator-ready audit packs on demand.

## 2. Why ECS exists (problems it solves)

| Problem | ECS answer |
|---|---|
| Evidence collected manually, repeatedly, per audit | **Connectors** auto-collect; **reuse intelligence** maps one artifact to many controls/frameworks |
| No single readiness number | **Audit Readiness Score** (coverage·0.5 + approval·0.3 + freshness·0.2) |
| Audits are fire-drills | **Audit Prep** cockpit + 30 pre-built audit packs |
| Compliance invisible to executives | Persona dashboards (CIO, heads, enterprise, Pan-India, ROI) |
| AI systems ungoverned | **AI SDLC governance** + **AI Governance posture** |
| Evidence decays silently | **Evidence Health / Lifecycle / Completeness** engines |

## 3. How ECS differs

| vs. | Difference |
|---|---|
| Traditional **GRC tools** | ECS auto-*collects* evidence from source systems, not just tracks tasks |
| **Audit tools** | ECS is continuous (always audit-ready), not point-in-time |
| **Evidence repositories** | ECS adds reuse intelligence, validation workflow, and readiness scoring on top of storage |

## 4. The five governance lifecycles

1. **Evidence lifecycle** — collect → validate → approve/reject → reuse → expire/refresh.
2. **Audit lifecycle** — prepare → readiness scoring → mock audit → audit pack → observation tracking.
3. **Compliance lifecycle** — onboard framework → map controls → measure coverage/maturity.
4. **Risk lifecycle** — register → assess → exception/TD governance → remediate.
5. **AI-SDLC lifecycle** — requirements → design → development → testing → go-live gates with evidence.

## 5. Personas (12 login + system roles)

CIO · Vertical Head · Functional Head · Compliance Head · App Owner · Auditor · Operations Owner · Framework Owner · Governance Lead · Risk · AI SDLC Owner · AI Governance Owner (+ Admin, Control Owner). Full capability matrix in `ECS_PERSONA_GUIDE.md`.

## 6. Modules (7 navigation groups)

Executive Overview · Frameworks · Operations · Governance · Evidence Governance (repo-backed) · Enterprise GRC · AI SDLC Governance. Deep reference: `docs/product_manual/ECS_MODULE_REFERENCE.md`.

## 7. Top dashboards & what they tell you

| Dashboard | Tells you |
|---|---|
| CIO Dashboard | Enterprise compliance + audit posture |
| Demo Overview | One-screen story for prospects |
| Enterprise / Pan-India | BU- and region-level posture |
| ROI Center | Value: hours saved, FTE, payback |
| Audit Prep | Are we ready for the next audit |
| Evidence Health | Is our evidence fresh and valid |
| Evidence Reuse | How much we collect-once-reuse-many |
| AI Governance | Is our AI usage compliant |

## 8. Reports

30 executive audit packs + 5 interactive HTML reports + 6 AI-SDLC reports + gap/comparison and onboarding exports. See `ECS_FEATURE_REFERENCE.md`.

## 9. How it runs (one paragraph)

FastAPI + Jinja2 server-rendered UI (no Node build), Python 3.12, optional Postgres/pgvector/MinIO/Redis via Docker Compose. **Demo mode** (`DEMO_MODE=true`, `ECS_AUTH_ENABLED=false`) runs the entire product on deterministic synthetic data with no external dependency. Real mode uses 12 connectors and a Postgres evidence repository.

## 10. New-joiner cheat sheet

- Start: `docs/DEMO_MODE_SETUP.md` → open `/dashboard/cio`.
- Learn the chain in §1; everything else is a view on it.
- "Collect once, reuse everywhere" is the whole thesis.
- Demo flow: Demo Overview → CIO Dashboard → a Framework page → Evidence Reuse → Audit Prep → Reports.
