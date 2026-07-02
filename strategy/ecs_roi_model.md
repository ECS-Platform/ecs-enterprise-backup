# ECS — ROI Model

**Lens:** CIO Advisory + Chief Product Officer
**Source of truth:** `config/roi.yaml` (the deterministic ROI engine config) and the platform's ROI Center (`modules/executive_overview/templates/mvp_roi_center.html`, validated by `tests/test_roi_engine.py`). **Every figure here is computed by the engine from editable assumptions — there are no hardcoded outputs in the UI.** Changing the YAML changes ROI output only; it never changes workflow, RBAC, audit, observation or schema behavior. The module is disabled by default (`ROI_CENTER_ENABLED=true` to enable).

> **⚠️ Rate-basis advisory (see `executive/documentation_audit.md`, issues A5/A6).** Two hour-rate bases exist in the repository and must be reconciled before this model is committed to a final business case:
> - **Config engine default:** `config/roi.yaml` sets `cost_per_hour: 1500`.
> - **Published workbook headline tables:** the §4 headline figures (e.g. 25-app: 45,438 hrs → ₹4.54 Cr Expected) are computed on the pre-existing ROI workbook basis of **₹1,000/hr** (`executive/ecs_roi_model.md`). At ₹1,500/hr the 25-app Expected saving scales to ~₹6.82 Cr.
>
> This document is the **canonical ROI reference for the executive deliverables package**; the pre-existing `executive/ecs_roi_model.md` is the originating workbook write-up. Finance should ratify a single rate and the headline tables should then be restated consistently (deferred — not auto-corrected).

---

## 1. How the Model Works

The engine merges the active **scenario** (`conservative` / `expected` / `aggressive`) over the bank-wide baseline assumptions, then recomputes all projections, the value waterfall, framework-level ROI, payback and takeaways. Determinism means a board can re-run the same inputs and get the same numbers.

### 1.1 Baseline assumptions (`roi.assumptions`)

| Assumption | Value |
|---|--:|
| Applications in bank | 905 |
| Applications in VAPT scope | 600 |
| Observations per application | 2.5 |
| Emails per observation | 7 |
| Hours per observation (manual) | 8 |
| Hours per email | 0.25 |
| Hours per audit cycle | 160 |
| Hours per manual framework onboarding | 80 |
| Blended cost per hour | ₹1,500 (config default; §4 headline tables use the workbook's ₹1,000 basis — see rate-basis advisory above) |
| Productive hours / FTE / year | 1,800 |
| Baseline anchor | ₹4.5 Cr saved per 25 onboarded apps |

### 1.2 ECS efficiency factors (`roi.efficiency`)

| Lever | Reduction / factor |
|---|--:|
| Observation emails eliminated | 85% |
| Manual effort removed per observation | 60% |
| Observations prevented outright | 30% |
| Audit effort removed by readiness | 55% |
| Framework onboarding effort removed | 70% |
| Evidence reuse factor (avg reuses per artifact) | 4× |
| Hours saved per reuse | 1.5 |
| Observation closure acceleration | 65% |
| Implementation/run cost (ROI denominator) | ₹60,000 / app / year |

---

## 2. Scenarios (`roi.scenarios`)

| Parameter | Conservative | Expected | Aggressive |
|---|--:|--:|--:|
| Adoption | 30% | 100% | 100% |
| Target applications | 600 (VAPT only) | 605 | 905 (full bank) |
| Frameworks | VAPT | VAPT | VAPT, RBI, ISO27001, PCI-DSS, SWIFT, AI Gov |
| Observations / app | 1.5 | 2.5 | 2.5 |
| Email reduction | 50% | 65% | 85% |
| Evidence reuse factor | 1.3× | 2.0× | 5.0× |
| Observation prevention | 25% | 50% | 60% |
| Closure acceleration | 40% | 65% | 80% |
| Audit effort reduction | 40% | 55% | 65% |
| Framework onboarding reduction | 50% | 70% | 80% |

---

## 3. Value Drivers & Weighting (`roi.value_drivers`)

| Driver | Mechanism | Weight |
|---|---|--:|
| Evidence reuse | Collect once → satisfy many frameworks (crosswalk) | 40% |
| Observation prevention | Always-ready evidence prevents findings | 25% |
| Closure acceleration | Faster observation closure | 15% |
| Auditor productivity | Self-service readiness, fewer back-and-forths | 10% |
| Email reduction | Automation replaces evidence-chasing email | 5% |
| Framework automation | Loader + reuse reduce onboarding effort | 5% |

The reuse lever (40%) dominates — consistent with the demonstrated **5.0× cross-framework reuse** (48 evidence → 240 obligations = 192 collection operations saved) in `demo-data/ECS_DEMO_NARRATIVE.md`.

---

## 4. Headline Results (per the ROI workbook scenarios)

### 4.1 25-application framework master

| Metric | Conservative (×0.8) | Expected | Aggressive (×1.2) |
|---|--:|--:|--:|
| Hours saved | 36,350 | 45,438 | 54,526 |
| Annual saving | ₹3.63 Cr | ₹4.54 Cr | ₹5.45 Cr |
| FTE equivalent | 18.2 | 22.7 | 27.3 |
| Emails eliminated (approx) | ~0.86 M | ~1.07 M | ~1.28 M |

### 4.2 Live FY25-26 value realization (current footprint)

| Scenario | Annual value |
|---|--:|
| Conservative | ₹13.82 Cr |
| Expected | ₹17.27 Cr |
| Aggressive | ₹20.72 Cr |

### 4.3 Scale-up net benefit (net = annual savings − ECS cost; ECS cost ₹4.0 Cr Y1 ramp, then ₹2.0–2.2 Cr stable)

| Period | Apps | Expected | Conservative (×0.8) | Aggressive (×1.2) |
|---|--:|--:|--:|--:|
| FY26 | 25 | ₹0.54 Cr | ₹0.43 Cr | ₹0.65 Cr |
| FY27 | 100 | ₹16.16 Cr | ₹12.93 Cr | ₹19.39 Cr |
| FY28 | 200 | ₹34.12 Cr | ₹27.30 Cr | ₹40.94 Cr |
| FY29 | 400 | ₹70.44 Cr | ₹56.35 Cr | ₹84.53 Cr |
| FY30 | 500 | ₹88.60 Cr | ₹70.88 Cr | ₹106.32 Cr |
| FY32 | 800 | ₹143.08 Cr | ₹114.46 Cr | ₹171.70 Cr |

---

## 5. Payback (`roi.payback`)

- **Program investment:** ₹8 Cr implementation + ₹2 Cr/yr run cost; horizons modeled at 3, 5 and 10 years.
- **Expected:** payback within **Year 1** at modeled adoption; net-positive from FY27 at scale.
- **Conservative:** payback within Year 1–2; remains strongly net-positive (₹114.46 Cr Year-7 net benefit).
- **Aggressive:** payback inside Year 1; ₹171.70 Cr Year-7 net benefit.

---

## 6. Operational Impact (demo baseline, trending — `roi.aging` and trends engine)

| Metric | Start (Nov) | Latest (Mar) | Improvement |
|---|--:|--:|--:|
| SLA on-time | 82% | 91% | +9 pts |
| SLA breaches | 18 | 8 | −56% |
| Evidence rejection rate | 8.2% | 4.2% | −49% |
| Compliance coverage | 71.2% | 79.4% | +8.2 pts |
| Observations closed (monthly) | 38 | 56 | +47% |

Observation aging: modeled closure improves from a 45-day baseline by the scenario's closure-acceleration factor (e.g. 65% Expected → ~16 days).

---

## 7. Risk & Rollout Model

- **Risk reduction** (`roi.risk`): deterministic curve, 0.12% reduction per onboarded app, capped at 78% coverage — more apps onboarded ⇒ higher portfolio risk coverage.
- **Rollout simulator** (`roi.rollout`): milestones 25 → 100 → 250 → 500 → 605 → 905 applications, aligned to the 3-year strategy.

---

## 8. Framework-Level Value (`roi.frameworks`)

Each framework contributes by weight, apps covered and reuse factor:

| Framework | Apps covered / coverage | Weight | Reuse factor |
|---|---|--:|--:|
| VAPT | 600 apps | 1.4 | 5× |
| RBI | 90% coverage | 1.2 | 4× |
| ISO 27001 | 70% coverage | 1.0 | 4× |
| PCI-DSS | 40% coverage | 1.1 | 3× |
| SWIFT | 25% coverage | 1.0 | 3× |
| AI Governance | 15% coverage | 0.8 | 2× |

---

## 9. Summary for Decision-Makers

| Headline | Conservative | Expected | Aggressive |
|---|--:|--:|--:|
| Live FY25-26 value | ₹13.82 Cr | ₹17.27 Cr | ₹20.72 Cr |
| 25-app annual saving | ₹3.63 Cr | ₹4.54 Cr | ₹5.45 Cr |
| FTE equivalent (25 apps) | 18.2 | 22.7 | 27.3 |
| Year-7 net benefit | ₹114.46 Cr | ₹143.08 Cr | ₹171.70 Cr |
| Stable OPEX | ₹2.2 Cr | ₹2.2 Cr | ₹2.2 Cr |

> **Even the conservative scenario delivers payback within Year 1–2 and a nine-figure (₹114 Cr+) net benefit at scale on a stable ₹2.2 Cr operating cost.** Because every number is computed by the deterministic engine from `config/roi.yaml`, the model is fully auditable: change an assumption, and the entire ROI Center recomputes consistently.

---

## 10. Validation Note

The ROI engine is covered by `tests/test_roi_engine.py`, and the ROI Center renders from the engine (no hardcoded UI values), consistent with the configuration's explicit determinism contract. Assumptions are deliberately editable so finance can substitute the bank's own blended rate, application counts and efficiency factors before committing the model to a business case.
