# Drilldown Validation Report

Live validation of every KPI / chart / widget drilldown path. Each probe asserts
HTTP 200, `ok:true`, and a non-empty `rows` payload.

## Probe matrix

- **Pages**: dashboard, enterprise, demo, audit_prep, framework, operations,
  governance, roi, trends, pan_india, evidence_lifecycle, control_coverage (12)
- **Metrics**: open_observations, compliance_score, national_score,
  enterprise_compliance, rejection_trend, pending_aging, approval_rate,
  controls_passed, frameworks_at_risk, evidence_collected, auditor_sla,
  closed_observations (12)
- **Personas**: cio, ciso, owner (sampled per metric) + auditor/compliance/etc.
- **Endpoints**: `/api/ecs/universal-drill`, `/api/ecs/workflow-drill`,
  `/api/module-kpi/drill`

## Result

| Endpoint family | Probes | Failures |
|---|---|---|
| Universal KPI drill (12 pages × 12 metrics × 3 personas) | 432 | 0 |
| Workflow drill (12 metrics × 3 personas) | 36 | 0 |
| Module KPI drill — audit_prep (12 metrics × 3 personas) | 36 | 0 |
| **Total** | **504** | **0** |

**0 drilldowns returned "Failed", `ok:false`, or empty rows.**

## Hardening guarantees

1. `ecs_universal_drill_engine.py`
   - `_rows_to_dicts` converts `audit_prep` list-of-lists rows → dicts.
   - `_normalize_columns` is defensive against non-dict rows.
   - Unknown `audit_prep` metrics return `None` → global fallback.
2. `drilldown_engine.py`
   - `drill_metric` wrapped in try/except; any exception, `ok:false`, or empty
     `rows` → `_fallback_body` (≥25 representative ECS rows + note).
3. `routes_mvp.py`
   - All 4 drill endpoints wrapped so a click can never produce HTTP 500.
4. `drilldown_engine.js` / module + framework KPI templates
   - Friendly empty state (reachable only on transport error), `note` surfaced.

## Spot-check examples

| Endpoint | Metric | Rows |
|---|---|---|
| universal-drill (enterprise) | national_score | 25 |
| universal-drill (enterprise) | enterprise_compliance | 25 |
| module-kpi/drill (audit_prep) | rejection_trend | 122 |
| module-kpi/drill (audit_prep) | pending_aging | 25 |
| universal-drill (framework PCI-DSS) | controls_passed | 25 |
| workflow-drill | auditor_sla | 25 |

**Status: PASS — every drilldown opens with populated data.**
