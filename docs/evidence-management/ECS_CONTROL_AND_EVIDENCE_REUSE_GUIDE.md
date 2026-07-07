# ECS Control & Evidence Reuse Guide

**Type:** Knowledge documentation. No code modified.
**Date:** 2026-06-17
**Grounding:** `modules/operations/engines/evidence_repository.py`,
`modules/frameworks/engines/framework_catalog.py`, evidence workflow engines.
Items not in code are marked **(Inferred from implementation)**.

The central value proposition of ECS: **define a control once, satisfy many
frameworks; collect evidence once, reuse it across many controls, frameworks, and
audits.** This eliminates duplicate work and shrinks audit effort.

---

## 1. Control reuse — one control → many frameworks

A single technical control (e.g. *Encryption at Rest*) maps to requirements in
multiple regulatory frameworks. ECS stores controls with a
`framework_coverage` string parsed into a `frameworks[]` list, so the same
control is surfaced under every framework it satisfies.

### Worked example — Encryption at Rest

| Framework | Mapped requirement (representative) |
|-----------|--------------------------------------|
| PCI DSS | Req 3 — Protect stored cardholder data (TDE / KMS) |
| C-SITE | Data-at-rest protection / cryptographic controls |
| DPSC | Data protection & encryption controls |
| ISG | Information classification → encryption mandate |
| ITPP | Production data protection in change/IT processes |

One execution of the encryption-at-rest check (e.g. PostgreSQL TDE / `SHOW ssl`)
produces one evidence artifact that is tagged to all five frameworks.

### Control concepts

| Concept | Where implemented | Meaning |
|---------|-------------------|---------|
| **Control Library** | `ECS_Query_Driven_Control_Library_Consolidated.xlsx` via `predefined_queries_engine.py` | Master catalog of controls + queries |
| **Control Catalog** | `framework_catalog.py` (`get_merged_framework_catalog`) | Per-framework control structure + evidence templates |
| **Control Reuse** | `framework_coverage` → `frameworks[]` | One control row referenced by many frameworks |
| **Control Ownership** | `OWNERS` / `REVIEWERS` in catalog; RBAC `control_owner` | Accountable owner per control |
| **Control Lineage** | execution history + audit trail | Control → executions → evidence → frameworks |

## 2. Evidence reuse — one evidence → many controls / frameworks / audits

`evidence_repository._link_reuse` groups evidence by standardised filename into
`REUSE-###` groups and records `linked_controls` (each with `framework` +
`control`). The result: a single evidence artifact is linked to multiple
controls and frameworks, and is reusable across audit cycles.

```
Evidence (EVD-#####)
  ├─ reuse_group: REUSE-###
  ├─ framework_tags: [PCI-DSS, DPSC, CSITE, ...]
  ├─ application_tags: [Net Banking, ...]
  └─ linked_controls: [{PCI: Req3}, {DPSC: Log Monitoring}, {CSITE: SIEM Alerts}, ...]
```

| Relationship | Mechanism |
|--------------|-----------|
| One evidence → many controls | `evidence_reuse_map[key].linked_controls` |
| One evidence → many frameworks | `framework_tags[]` + linked-control frameworks |
| One evidence → many audits | persistent evidence + `version` chain reused across audit periods **(Inferred from implementation)** |

## 3. Evidence lifecycle

`register_upload` sets `lifecycle: "Draft"`, `version: 1`, `status: "Uploaded"`,
`reviewer: "Pending Assignment"`. Records then progress through the evidence
workflow (collection → validation → submission → review → approval/rejection →
current/expired). Lifecycle stages drive the Evidence Lifecycle and Evidence
Health dashboards.

## 4. Evidence lineage & traceability

* **Lineage:** evidence carries `control`, `framework_tags`, `application_tags`,
  `uploaded_by`, `uploaded_at`, `sha256`, `version`, `reuse_group` — a complete
  provenance chain from source to control to framework.
* **Traceability:** `get_reuse_graph` returns nodes/edges of evidence↔control
  links; the audit trail (`log_event`, `record_version`) records every state
  change; predefined-query executions add `PQ-EXEC`/`PQ-EVD` identifiers.
* **Integrity:** SHA-256 + `integrity_check` provide tamper-evidence on every
  artifact.

## 5. Evidence reuse metrics

Derived from the reuse map and repository (surfaced on Evidence Reuse / Health
dashboards):

| Metric | Definition |
|--------|------------|
| Reuse groups | count of `REUSE-###` groups |
| Reused artifacts | evidence with `reused: true` |
| Avg controls per evidence | mean `len(linked_controls)` per group |
| Cross-framework coverage | distinct frameworks per reuse group |
| Duplication avoided | (controls served) − (unique artifacts) **(Inferred from implementation)** |

## 6. Evidence duplication reduction

Because one artifact is linked to many controls, ECS avoids collecting the same
evidence separately per framework. Duplication reduction = controls satisfied
minus unique artifacts stored. The standardised naming (`enforce_naming`) plus
content hashing (`compute_hash`) make identical artifacts converge into one reuse
group rather than many duplicates.

## 7. Audit effort reduction

| Driver | Effect |
|--------|--------|
| Control reuse | one control authored once covers N frameworks → fewer controls to maintain |
| Evidence reuse | one artifact answers N controls across M audits → fewer collection tasks |
| Predefined automation | repeatable execution replaces manual evidence gathering |
| Lineage + integrity | auditors trust provenance → faster sign-off |
| Cross-framework mapping | a single audit cycle pre-populates adjacent framework audits |

**Net:** audit preparation shifts from per-framework manual collection to
**collect-once, map-many, reuse-across-audits**, materially reducing effort
(quantified on the ROI / Value Realization dashboards).

## 8. Current vs inferred vs recommended

| Area | Current | Inferred | Recommended |
|------|---------|----------|-------------|
| Reuse grouping | filename-key grouping + seeded cross-framework links | content-hash dedup convergence | Promote hash-based dedup as primary key |
| Reuse metrics | reuse map + dashboards | duplication-avoided / effort-saved | Add explicit reuse-savings KPI to ROI pack |
| Versioning | `version` + `record_version` ledger | supersede chain across audits | Persist immutable version history in Postgres |
