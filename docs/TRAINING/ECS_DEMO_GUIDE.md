# ECS Demo Guide (Knowledge Transfer)

**Audience:** demo teams, presales, new joiners running their first demo. **Goal:** deliver a flawless ECS demo solo. Backed by `demo-data/ECS_DEMO_NARRATIVE.md` and a live validator (READY, 0 defects).

---

## 1. One-time setup (2 minutes)

```bash
cp .env.example .env
export DEMO_MODE=true ECS_AUTH_ENABLED=false
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# Validate before presenting:
DEMO_MODE=true ECS_AUTH_ENABLED=false ./venv/bin/python scripts/validate_demo_readiness.py   # expect READY
```

No database, connectors, or internet required — demo mode is fully self-contained on deterministic synthetic banking data.

## 2. The golden path (15–20 min)

| # | Screen | Say this |
|---|---|---|
| 1 | Login `/` | "Pick any persona — ECS is role-aware." |
| 2 | Demo Overview `/mvp/demo-overview` | "One screen: apps, frameworks, controls, evidence, AI, VAPT." |
| 3 | CIO Dashboard `/dashboard/cio` | "Board-level posture: compliance, audit completion, readiness." |
| 4 | A Framework page `/framework/PCI DSS` | "Per-regulation: maturity, QSA readiness, control + evidence." |
| 5 | Evidence Reuse `/mvp/reuse` | "The thesis: collect once, satisfy many frameworks." |
| 6 | Audit Prep `/mvp/audit-prep` | "Always audit-ready — generate the audit pack live." |
| 7 | Reports `/mvp/reports` | "30 regulator-ready packs on demand." |
| 8 | AI Governance `/mvp/ai-governance` | "We govern AI usage too." |
| 9 | ROI Center `/mvp/roi` | "Here's the money: hours saved, FTE, payback." |

## 3. Persona deep-dives (optional)

- **Auditor:** `/evidence/review` → approve evidence → `/mvp/evidence-approval` throughput.
- **Compliance:** `/mvp/completeness` → close a gap → coverage rises.
- **AI SDLC Owner:** `/mvp/ai-sdlc/control-tower` → stage readiness → go-live gate.
- **Risk/Governance:** `/mvp/risk-register`, `/mvp/exception-governance`.

## 4. The talk track for KPIs

Use `docs/TRAINING/ECS_KPI_REFERENCE.md` for any KPI a prospect asks about (definition + business meaning + good/warning/critical bands).

## 5. Do / Don't

| Do | Don't |
|---|---|
| Run the validator first | Demo on a phone (sub-768px not polished) |
| Demo on desktop/projector | Quote both demo-seed and catalog counts (pick one) |
| Drill into any tile (all work) | Enable real connectors live (use demo data) |
| Show lineage on evidence | Promise capabilities marked "target/L4-L5" in maturity assessment |

## 6. If something looks off

- Re-run `validate_demo_readiness.py` (should be READY).
- Confirm `DEMO_MODE=true` and `ECS_AUTH_ENABLED=false`.
- Check `/healthz`. See `docs/AUDIT/ECS_DEMO_READINESS_REPORT.md` for the full checklist.

## 7. Honesty guardrails

ECS is **L3 (Defined), trending L4** (`product/product_maturity_assessment.md`). Present delivered features confidently; frame agentic AI, no-code workflow designer, external auditor portal, and mobile responsiveness as **roadmap**, not shipped.
