# ECS Sequence Diagram Library

**Type:** Architecture / auditor-grade sequence reference. No code modified.
**Date:** 2026-06-17
**Grounding:** workflow engines, evidence repository, predefined-query engines,
exception governance, framework workflow engine. Inferred interactions are noted.

**Navigation:** [Workflow Orchestration Guide](ECS_WORKFLOW_ORCHESTRATION_GUIDE.md) ·
[State Transition Matrix](ECS_STATE_TRANSITION_MATRIX.md) ·
[Role Action Matrix](ECS_ROLE_ACTION_MATRIX.md) ·
[Predefined Query Execution Workflow](../OPERATIONS/ECS_PREDEFINED_QUERY_EXECUTION_WORKFLOW.md)

---

## 1. Evidence lifecycle

```mermaid
sequenceDiagram
    participant AO as Application Owner
    participant ENG as Evidence Workflow Engine
    participant REP as Evidence Repository
    participant AU as Auditor
    participant AT as Audit Trail
    AO->>REP: register_upload(file)
    REP->>REP: compute_hash + enforce_naming + integrity_check
    REP->>AT: log_event("Evidence Uploaded")
    AO->>ENG: record_transition("submitted")
    ENG->>AU: Pending Auditor Approval queue
    AU->>ENG: record_transition("approved")
    ENG->>ENG: close_observations_for_control()
    ENG->>AT: log_event("Observation Closed")
    ENG-->>AO: toast_payload("approved")
```

## 2. Audit lifecycle

```mermaid
sequenceDiagram
    participant AM as Audit Manager
    participant ECS as ECS Audit Prep
    participant OW as Owners
    participant AU as Auditor
    participant EX as Executives
    AM->>ECS: define audit scope (frameworks + apps)
    ECS->>OW: evidence requests / predefined queries
    OW->>ECS: evidence submitted
    AU->>ECS: review + raise findings
    ECS->>OW: remediation / RAF
    OW->>ECS: re-validated evidence
    ECS->>AM: audit package compiled
    AM->>EX: sign-off + report
```

## 3. Observation lifecycle

```mermaid
sequenceDiagram
    participant SYS as ECS (missing evidence)
    participant OW as Owner
    participant AU as Auditor
    SYS->>SYS: observation opened (missing_evidence_registry)
    SYS->>OW: assign observation
    OW->>OW: remediate + collect evidence
    OW->>AU: submit (Pending Validation)
    AU->>SYS: approve → close_observations_for_control()
    SYS-->>OW: observation Closed
```

## 4. Framework lifecycle

```mermaid
sequenceDiagram
    participant CO as Compliance
    participant FW as Framework Workflow Engine
    participant CT as Controls
    participant AU as Auditor
    CO->>FW: framework In Progress
    FW->>CT: evaluate per-control state (_infer_control_state)
    CT-->>FW: approved/submitted/reupload/draft
    FW->>FW: readiness = 0.45*impl + 0.35*evidence + 0.20*risk
    FW-->>CO: readiness >= target → Completed
    CO->>AU: request sign-off → Approved
```

## 5. Control lifecycle

```mermaid
sequenceDiagram
    participant OW as Owner
    participant CT as Control
    participant AU as Auditor
    participant EX as Exception Gov
    CT->>CT: Applicable
    OW->>AU: evidence submitted
    AU->>CT: approve → Compliant
    AU->>CT: reject → Non-Compliant
    CT->>EX: raise exception (Non-Compliant)
    EX->>CT: RAF approved → Risk Accepted
```

## 6. RAF lifecycle

```mermaid
sequenceDiagram
    participant OW as Owner
    participant ISG as ISG / Compliance
    participant CIO as CIO
    participant MON as Monitoring
    OW->>ISG: RAF raised (exception.raise)
    ISG->>ISG: ISG Review
    ISG->>CIO: route for approval
    CIO->>OW: RAF Approved (exception.approve) + expiry
    OW->>MON: active, periodic review
    MON->>OW: expiry reached → re-evaluate
```

## 7. Exception lifecycle

```mermaid
sequenceDiagram
    participant OW as Owner
    participant GOV as Governance
    participant AT as Audit Trail
    OW->>GOV: exception Raised
    GOV->>GOV: Under Review
    GOV->>OW: Active (with expiry) | Rejected
    GOV->>AT: log decision
    GOV->>GOV: Review Due → renew | Expired
```

## 8. Predefined query lifecycle

```mermaid
sequenceDiagram
    participant OP as Operator
    participant ENG as Query Engine
    participant CN as Connector
    participant TG as Target (YAML)
    participant CC as connector_common
    participant REP as Evidence Repository
    OP->>ENG: execute control (allow-listed)
    ENG->>CN: route by technology
    CN->>TG: connect + execute
    TG-->>CN: ConnectorResult
    CN->>CC: complete_connector_execution
    CC->>REP: audit + evidence + register_upload
    REP-->>OP: {ok, rows, evidence_id}
```

## 9. Evidence reuse lifecycle

```mermaid
sequenceDiagram
    participant REP as Evidence Repository
    participant RU as Reuse Map
    participant CTRL as Other Controls
    participant DEC as Reuse Decision (can_reuse_evidence_decision)
    REP->>RU: _link_reuse(record) → REUSE-### group
    RU->>CTRL: link evidence to additional controls/frameworks
    CTRL->>DEC: reuse requested for new control
    DEC-->>CTRL: evidence satisfies control without re-collection
```

## 10. Control reuse lifecycle

```mermaid
sequenceDiagram
    participant LIB as Control Library
    participant CAT as Framework Catalog
    participant FW as Frameworks
    participant EVD as Evidence
    LIB->>CAT: control defined once (framework_coverage)
    CAT->>FW: parsed to frameworks[] (resolve_framework_name)
    FW->>EVD: one execution/evidence per control
    EVD-->>FW: satisfies all mapped frameworks simultaneously
```
