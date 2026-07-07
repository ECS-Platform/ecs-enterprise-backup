# ECS Workflow Orchestration Guide

**Type:** Enterprise / auditor / architecture-grade documentation. No code modified.
**Date:** 2026-06-17
**Grounding:** `modules/shared/services/evidence_workflow_engine.py`,
`modules/frameworks/engines/framework_workflow_engine.py`, `config/rbac.yaml`,
`modules/shared/services/audit_trail.py`, `app/audit/workflow.py`,
`modules/operations/engines/*` (predefined queries). Workflows not fully
implemented in code are labelled **"Inferred Enterprise Workflow."**

**Navigation:** [Role Action Matrix](ECS_ROLE_ACTION_MATRIX.md) ·
[State Transition Matrix](ECS_STATE_TRANSITION_MATRIX.md) ·
[SLA & Escalation Matrix](ECS_SLA_ESCALATION_MATRIX.md) ·
[Notification Matrix](ECS_NOTIFICATION_MATRIX.md) ·
[Business Process Model](ECS_BUSINESS_PROCESS_MODEL.md) ·
[Sequence Diagrams](ECS_SEQUENCE_DIAGRAMS.md) ·
[Predefined Query Execution Workflow](../operations/ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md) ·
[Predefined Query Execution Guide](../operations/ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md) ·
[Control & Evidence Reuse](../evidence-management/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md) ·
[Framework Reference](../product/ECS_FRAMEWORK_REFERENCE.md)

---

## Canonical workflow vocabulary (grounded)

ECS state labels come directly from `evidence_workflow_engine.OWNER_STATES` /
`AUDITOR_STATES` and the `ecs_state` registries:

- Owner states: `Draft → Uploaded → Pending App Owner Approval → Pending Auditor
  Approval → Needs Rework → Rejected → Closed`.
- Auditor states: `Pending Auditor Approval → Closed | Rejected By Auditor |
  Needs Rework | Escalated | Exception Raised`.
- Action→status map (`record_transition` / `_action_to_status`): `submitted →
  Pending Auditor Approval`, `approved → Closed`, `rejected → Rejected By
  Auditor`, `reupload → Needs Rework`, `owner_approved → Pending Auditor
  Approval`, `owner_rejected → Rejected By App Owner`.
- Capability gates (`config/rbac.yaml` `rbac_legacy_compat.capabilities`):
  `can_upload_evidence`, `can_submit_to_auditor`, `can_review_evidence`,
  `can_request_reupload`, `can_escalate`, `can_raise_exception`,
  `can_assign_owner`, `can_export_reports`, `can_manage_frameworks`.

Every audited mutation is logged via `audit_trail.log_event` and (flag-gated)
`app/audit/workflow.audit_workflow_action`.

---

## 1. End-to-end ECS business workflow

```mermaid
flowchart TD
    A[Framework onboarded / selected] --> B[Controls mapped to applications]
    B --> C{Evidence source?}
    C -->|Manual| D[App Owner uploads evidence]
    C -->|Automated| E[Predefined query executes → evidence auto-filed]
    C -->|Connector| F[Connector sync ingests evidence]
    D --> G[Evidence validation: hash + naming + integrity]
    E --> G
    F --> G
    G --> H[Submitted to Auditor]
    H --> I{Auditor decision}
    I -->|Approve| J[Closed → Observation auto-closed]
    I -->|Reject / Re-upload| K[Needs Rework → back to App Owner]
    I -->|Escalate| L[Escalated to FH/VH/CISO]
    I -->|Exception| M[RAF / Exception governance]
    K --> D
    J --> N[Framework readiness + KPIs recompute]
    M --> N
    N --> O[Audit Dashboard + Executive Dashboard]
```

## 2. Evidence submission workflow

`App Owner → Upload → Validation → Auditor Review → Approval/Rejection`
(grounded in `register_upload`, `resolve_state`, `record_transition`,
`close_observations_for_control`).

```mermaid
flowchart LR
    O[Application Owner] -->|can_upload_evidence| U[Upload Evidence]
    U --> V[Validation: SHA-256, naming policy, integrity]
    V -->|can_submit_to_auditor| S[Submitted — Pending Auditor Approval]
    S --> R{Auditor Review}
    R -->|approve| AP[Closed]
    R -->|reject / reupload| RW[Needs Rework]
    RW --> U
```

Swimlane:

```mermaid
sequenceDiagram
    participant AO as Application Owner
    participant ECS as ECS Workflow Engine
    participant AU as Auditor
    AO->>ECS: Upload evidence (register_upload)
    ECS->>ECS: compute_hash + enforce_naming + integrity_check
    AO->>ECS: Submit to auditor (record_transition "submitted")
    ECS->>AU: Appears in Pending Auditor Review queue
    AU->>ECS: Approve (record_transition "approved")
    ECS->>ECS: close_observations_for_control()
    ECS-->>AO: Toast "Evidence Approved" + Observation closed
```

## 3. Evidence rejection workflow

`Submit → Auditor Reject → Comments → Resubmission → Re-review`
(grounded: `rejected_controls`, `clarification_controls` `reupload_requested`,
`toast_payload("reupload")`).

```mermaid
stateDiagram-v2
    [*] --> Submitted
    Submitted --> RejectedByAuditor: reject (comments required)
    Submitted --> NeedsRework: reupload requested
    RejectedByAuditor --> NeedsRework
    NeedsRework --> Submitted: App Owner resubmits corrected evidence
    Submitted --> Closed: approve
    Closed --> [*]
```

Auditor comments are persisted on the transition (`detail`/`comments` in
`record_transition`) and surfaced in the approval trail.

## 4. Function Head approval workflow — **Inferred Enterprise Workflow**

`functional_head` is read/analytics/export scoped to its function
(`role_scope: function`). The approval gate is an enterprise overlay:

```mermaid
flowchart LR
    A[Auditor-approved evidence in function scope] --> B[FH review pack]
    B --> C{Function Head}
    C -->|Endorse| D[Function attestation recorded]
    C -->|Return| E[Back to Auditor/Owner with comments]
    D --> F[Roll-up to Vertical Head]
```
*Inferred:* code grants FH read/export + escalation; sign-off is a governance
attestation (recommended Phase 2 enforcement).

## 5. Vertical Head approval workflow — **Inferred Enterprise Workflow**

`vertical_head` (`role_scope: vertical`) aggregates across owned vertical.

```mermaid
flowchart LR
    A[Function attestations across vertical] --> B[VH consolidated posture]
    B --> C{Vertical Head}
    C -->|Approve| D[Vertical sign-off → CIO/CISO roll-up]
    C -->|Escalate| E[Escalation to CISO/CIO]
```

## 6. CIO approval workflow — **Inferred Enterprise Workflow**

`cio` has enterprise scope + `exception.approve` (`rbac_catalog`).

```mermaid
flowchart LR
    A[Enterprise posture + open exceptions] --> B{CIO}
    B -->|Approve enterprise readiness| C[Audit-ready declaration]
    B -->|Approve exception / RAF| D[Risk accepted at enterprise level]
    B -->|Reject| E[Return to Vertical/Function]
```

## 7. CISO approval workflow — **Inferred Enterprise Workflow**

CISO maps to `security_officer` (security scope) with governance escalation
authority. Approves security exceptions, compensating controls, and risk
acceptance for security findings.

```mermaid
flowchart LR
    A[Security findings / VAPT / exceptions] --> B{CISO}
    B -->|Accept risk| C[RAF approved - security]
    B -->|Require compensating control| D[Compensating control workflow]
    B -->|Reject| E[Remediation mandated]
```

## 8. Risk acceptance workflow (RAF)

`Observation → RAF Raised → ISG Review → Approval → Expiry → Monitoring`
(grounded: `exception.raise`/`exception.approve`, `can_raise_exception`,
`active_exceptions`, `Exception Raised` auditor state; RAF naming is **Inferred
Enterprise Workflow** = exception governance).

```mermaid
stateDiagram-v2
    [*] --> Observation
    Observation --> RAFDraft: owner raises RAF (can_raise_exception)
    RAFDraft --> RAFSubmitted: submit
    RAFSubmitted --> ISGReview: ISG / governance review
    ISGReview --> Approved: approve (exception.approve)
    ISGReview --> Rejected: reject → remediation
    Approved --> Monitoring: active, periodic review
    Monitoring --> Expired: expiry date reached
    Expired --> Observation: re-evaluate / renew
    Rejected --> Observation
```

## 9. Observation closure workflow

Grounded in `close_observations_for_control` (auto-close on approval) and
`can_close_observation`.

```mermaid
flowchart LR
    A[Observation Open] --> B[Assigned to owner]
    B --> C[Remediation: evidence collected]
    C --> D[Pending Validation: submitted to auditor]
    D --> E{Auditor}
    E -->|approve| F[Closed - auto via close_observations_for_control]
    E -->|reject| C
    D --> G[Risk Accepted via RAF]
```

## 10. Framework assessment workflow

Grounded in `framework_workflow_engine._framework_metrics` (readiness =
0.45×implementation + 0.35×evidence + 0.20×risk component).

```mermaid
flowchart TD
    A[Framework Not Started] --> B[In Progress: controls being evidenced]
    B --> C[Per-control workflow: draft→submitted→approved]
    C --> D[Readiness score recompute]
    D --> E{Readiness >= target?}
    E -->|Yes| F[Completed]
    F --> G[Approved by Compliance/Auditor]
    E -->|No| B
```

## 11. Control assessment workflow

```mermaid
stateDiagram-v2
    [*] --> Applicable
    Applicable --> Compliant: evidence approved
    Applicable --> NonCompliant: evidence missing/rejected
    NonCompliant --> Exception: exception raised
    Exception --> RiskAccepted: RAF approved
    NonCompliant --> Compliant: remediated + approved
    Compliant --> [*]
```

## 12. Evidence reuse workflow

Grounded in `evidence_repository._link_reuse` / `get_reuse_graph`.

```mermaid
flowchart LR
    A[Evidence approved] --> B[_link_reuse: REUSE-### group]
    B --> C[Linked to multiple controls/frameworks]
    C --> D{Same control elsewhere?}
    D -->|Yes| E[Reuse decision - can_reuse_evidence_decision]
    E --> F[Evidence satisfies new control without re-collection]
    D -->|No| G[Remains primary artifact]
```

## 13. Control reuse workflow

```mermaid
flowchart LR
    A[Control defined once - framework_coverage] --> B[Parsed to frameworks list]
    B --> C[Surfaced under every mapped framework]
    C --> D[One execution/evidence satisfies all mapped frameworks]
```
See [Control & Evidence Reuse Guide](../evidence-management/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md).

## 14. Predefined query execution workflow

Grounded in `predefined_queries_engine`, `connector_common`,
`predefined_query_evidence`, `predefined_query_audit`.

```mermaid
sequenceDiagram
    participant U as Operator
    participant E as Predefined Query Engine
    participant C as Connector
    participant T as Target (YAML)
    participant R as Evidence Repository
    U->>E: Execute control (allow-listed)
    E->>C: route by detected technology
    C->>T: connect + execute query
    T-->>C: ConnectorResult
    C->>R: complete_connector_execution → audit + evidence + register_upload
    R-->>U: {ok, rows, evidence_id, evidence_filename}
```
Full detail: [Predefined Query Execution Workflow](../operations/ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md).

## 15. Exception management workflow

Grounded: `exception.raise`/`exception.approve`, `active_exceptions`,
exception drivers in framework metrics.

```mermaid
stateDiagram-v2
    [*] --> Raised
    Raised --> UnderReview: governance/ISG review
    UnderReview --> Active: approved (with expiry)
    UnderReview --> Rejected: denied → remediation
    Active --> ReviewDue: periodic review window
    ReviewDue --> Active: renewed
    ReviewDue --> Expired: not renewed
    Expired --> [*]
    Rejected --> [*]
```

## 16. Compensating control workflow — **Inferred Enterprise Workflow**

```mermaid
flowchart LR
    A[Control Non-Compliant] --> B[Propose compensating control]
    B --> C{CISO / ISG review}
    C -->|Approve| D[Compensating control active + evidence]
    C -->|Reject| E[Direct remediation required]
    D --> F[Linked to original control as mitigation]
    F --> G[Periodic re-validation]
```

## 17. Audit lifecycle workflow

Grounded: `audit_trail.log_event`, `app/audit/workflow`, audit-prep engines.

```mermaid
flowchart TD
    A[Audit planned] --> B[Scope: frameworks + applications]
    B --> C[Evidence collection + predefined queries]
    C --> D[Auditor review queue]
    D --> E[Findings/observations raised]
    E --> F[Remediation / RAF]
    F --> G[Re-validation]
    G --> H[Audit package compiled - audit prep]
    H --> I[Sign-off + report]
    I --> J[Executive dashboard + regulator submission]
```

## 18. Regulatory examination workflow — **Inferred Enterprise Workflow**

```mermaid
flowchart LR
    A[Regulator request - RBI/NPCI] --> B[Map request to frameworks/controls]
    B --> C[Pull reusable evidence + audit packages]
    C --> D[Compliance review + redaction]
    D --> E[Submission to regulator]
    E --> F[Findings → observations → remediation]
    F --> G[Status briefings - regulator liaison ISG-09]
```

## 19. Internal audit workflow

```mermaid
flowchart LR
    A[Internal audit plan v2026 - ISG-08] --> B[Self-assessment - ASST]
    B --> C[Evidence + predefined query execution]
    C --> D[Internal auditor review]
    D --> E[Observations + closure tracker]
    E --> F[Audit closure + management report]
```

## 20. External audit workflow

```mermaid
flowchart LR
    A[External auditor engaged - KPMG/PCI ASV] --> B[Read-only auditor access - scope enterprise]
    B --> C[Evidence export - export_evidence]
    C --> D[Sampling + testing]
    D --> E[Findings + remediation validation letters]
    E --> F[Attestation / certification]
```

---

## Cross-references
- Roles & permissions per action: [ECS_ROLE_ACTION_MATRIX.md](ECS_ROLE_ACTION_MATRIX.md)
- Valid state transitions: [ECS_STATE_TRANSITION_MATRIX.md](ECS_STATE_TRANSITION_MATRIX.md)
- SLA timers & escalation: [ECS_SLA_ESCALATION_MATRIX.md](ECS_SLA_ESCALATION_MATRIX.md)
- Notifications: [ECS_NOTIFICATION_MATRIX.md](ECS_NOTIFICATION_MATRIX.md)
- BPMN-style model: [ECS_BUSINESS_PROCESS_MODEL.md](ECS_BUSINESS_PROCESS_MODEL.md)
- Sequence diagrams: [ECS_SEQUENCE_DIAGRAMS.md](ECS_SEQUENCE_DIAGRAMS.md)
