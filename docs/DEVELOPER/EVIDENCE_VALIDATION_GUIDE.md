# ECS Evidence Validation Engine Guide

**Module:** Audit Intelligence — Milestone 2 (Evidence Validation Engine)
**Package:** `modules/audit_intelligence/engines/evidence_validation.py`

---

## 1. Purpose

Turn captured evidence into audit-meaningful outcomes, **deterministically and with
no LLM dependency**:

- **verdict:** `PASS` · `FAIL` · `WARNING` · `NOT APPLICABLE`
- **control status:** `Compliant` · `Non-Compliant` · `Needs Review` · `Not Assessed`
- **evidence quality:** `0.0 … 1.0` (was substantive evidence actually captured?)
- **compliance %** and **evidence quality score** aggregated over a set.

---

## 2. Rule model (deterministic)

Applied in order to each `EvidenceRecord`:

1. **Not configured** (`Connector Missing` / `Configuration Required`) →
   `NOT APPLICABLE` / `Not Assessed`, quality 0.
2. **Execution failed** (`ok=False`) → `FAIL` / `Non-Compliant`.
3. **Completed but empty** (no output, 0 rows) → `WARNING` / `Needs Review`.
4. **Assertion controls** (name/desc/query mentions TLS, SSL, encryption, audit,
   logging, MFA, cipher, protocol, …, or the output contains state keywords):
   - positive signal only (`enabled`, `on`, `true`, `required`, `scram-sha-256`,
     `TLSv1.2/1.3`, …) → `PASS` / `Compliant`.
   - negative signal only (`disabled`, `off`, `false`, `md5`, `TLSv1.0/1.1`,
     `sslv3`, …) → `FAIL` / `Non-Compliant`.
   - both → `WARNING` / `Needs Review` (mixed).
   - neither → `WARNING` / `Needs Review` (no clear signal).
5. **Inventory/enumeration controls** (evidence captured, no assertion) → `PASS` /
   `Compliant` (informational baseline evidenced).

Signal keyword lists live at the top of the module and are easy to extend.

### Evidence quality score

`0.0` if not configured; `0.1` if execution failed; else `0.5` base +`0.2` rows
+`0.2` output +`0.1` stored artifact (capped at `1.0`).

---

## 3. Aggregation

`compliance_summary(results)` returns totals, `by_verdict`, `by_control_status`,
`compliance_percent`, and `evidence_quality_score`.

- **compliance %** is over **assessed** controls only (PASS/FAIL/WARNING) —
  `NOT APPLICABLE` is excluded so unconfigured targets don't distort readiness.
- **PASS = 1.0, WARNING = 0.5, FAIL = 0** toward the percentage.

---

## 4. API

| Function | Purpose |
|---|---|
| `validate_record(record, control=None)` | validate one record → `ValidationResult` |
| `validate_records(records, controls_by_id=None)` | validate a list |
| `compliance_summary(results)` | aggregate percentages/counts |

Via the service: `evidence_service.validate_run(run_id)` validates a run's evidence,
folds each result back onto the run's records, and returns the compliance summary.

---

## 5. Usage

```python
from modules.audit_intelligence.engines import evidence_validation as val

results = val.validate_records(run.records, controls_by_id)
val.compliance_summary(results)
# {'compliance_percent': 66.7, 'evidence_quality_score': 0.71, 'passed': 4, ...}
```

---

## 6. Tests

`tests/test_evidence_validation.py` — every verdict path, evidence-quality scaling,
NA exclusion from compliance %, WARNING half-credit, serialization.

---

## 7. Assumptions & limitations

- Rules are **keyword/heuristic** over evidence text — intentionally deterministic
  and explainable (`rule_id` + `rationale` on every result). They are tuned for the
  current control catalog and are easy to extend per control family.
- Not a policy engine: complex/threshold checks (e.g. "TLS ≥ 1.2 AND cipher in
  allow-list") can be added as new rules later without changing the interface.
