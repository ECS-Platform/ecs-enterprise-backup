# ECS Entity-Relationship Diagrams

> Entities and attributes are reconstructed from actual code structures (dataclasses, Pydantic
> models, and the dict/tuple shapes used by mock-data engines and `ecs_state`). Because ECS uses a
> mixed typed/dict model and runs primarily on in-process state, these ER diagrams are a **logical
> model** of the implemented domain, not a physical SQL schema. Source files are cited per section.
> **[ASSUMPTION]** marks relationship cardinalities inferred from linkage fields (e.g. `linked_control`).

---

## 1. Users & Roles

Source: `app/auth/context.py`, `app/auth/roles.py`, `modules/shared/services/persona_display.py`.

```mermaid
erDiagram
  AUTHENTICATED_USER ||--o{ ROLE : has
  ROLE ||--o{ ROLE_ALIAS : "normalized via"
  ROLE ||--o{ PERSONA_PROFILE : "renders as"

  AUTHENTICATED_USER {
    string user_id
    string username
    string display_name
    string email
    tuple  roles
    tuple  groups
    string auth_source
  }
  ROLE {
    string key PK
    string title
    string description
    string scope "enterprise|vertical|function|application|control"
    string category
    list   aliases
  }
  ROLE_ALIAS {
    string alias PK
    string canonical_key FK
  }
  PERSONA_PROFILE {
    string role_key FK
    string display_name
    string role_title
    list   tabs
  }
```

---

## 2. Applications

Source: `modules/shared/services/ecs_state.py` (`BANKING_APPLICATIONS`),
`modules/frameworks/engines/framework_catalog.py` (`APPLICATIONS`),
`modules/ai_sdlc/engines/ai_sdlc_workflow_engine.py` (`_onboarded_applications`),
`modules/ai_sdlc/engines/ai_sdlc_governance_mock.py` (`AI_APPLICATIONS`).

```mermaid
erDiagram
  APPLICATION ||--o{ APP_FRAMEWORK : "assessed against"
  APPLICATION ||--o{ AI_APPLICATION : "AI variant"
  APPLICATION {
    string application_name PK
    string business_owner
    string application_owner
    string criticality
    string regulatory_classification
    int    control_count
  }
  AI_APPLICATION {
    string id PK
    string name
    string application FK
    string owner
    string business_unit
    string model
    string use_case
    string risk_tier
    float  compliance_score
    string model_status
    int    hallucinations_30d
    int    tokens_mtd
    string last_review
  }
  APP_FRAMEWORK {
    string application_name FK
    string framework FK
  }
```

---

## 3. Frameworks & Controls

Source: `modules/frameworks/engines/framework_catalog.py`,
`modules/governance/engines/governance_relational_model.py`,
`modules/shared/services/ecs_state.py`.

```mermaid
erDiagram
  FRAMEWORK ||--o{ CONTROL : contains
  FRAMEWORK ||--o{ FRAMEWORK_ALIAS : "resolved by"
  CONTROL ||--o{ EVIDENCE : "evidenced by"
  CONTROL ||--o{ FINDING : "may raise"

  FRAMEWORK {
    string framework_name PK
    string maturity_baseline
  }
  FRAMEWORK_ALIAS {
    string alias PK
    string framework_name FK
  }
  CONTROL {
    string control_id PK
    string control
    string control_description
    string application
    string owner
    string implementation
    string validation
    string workflow
    int    sla_days
  }
  EVIDENCE {
    string evidence_id PK
    string evidence_name
    string control_id FK
    string application
    string uploaded_by
    string evidence_status
    string audit_status
    string reviewer
    string expiry_date
    string evidence_source
    string environment
    string region
    string evidence_version
  }
```

---

## 4. Findings & Observations

Source: `modules/governance/engines/governance_relational_model.py`,
`modules/governance/engines/missing_evidence_engine.py`,
`modules/shared/services/evidence_workflow_engine.py` (`close_observations_for_control`).

```mermaid
erDiagram
  CONTROL ||--o{ FINDING : has
  CONTROL ||--o{ OBSERVATION : has
  OBSERVATION ||--o| CLOSED_OBSERVATION : "closed as"
  FINDING ||--o{ EVIDENCE : "linked_evidence"

  FINDING {
    string finding_id PK
    string application
    string observation
    string severity
    string source
    string integration
    string open_since
    string linked_control FK
    string linked_evidence FK
    string owner
    string status
    int    aging_days
    string closure_dependency
  }
  OBSERVATION {
    string observation_id PK
    string application
    string framework
    string control_id FK
    string missing_evidence
    string evidence_type
    string risk
    string observation_severity
    string due_date
    string status
    string owner
    string remediation_owner
  }
  CLOSED_OBSERVATION {
    string observation_id PK
    string framework
    string control
    string control_id FK
    string closed_by
    string closed_at
    bool   auto_closed
  }
```

---

## 5. Evidence (versioning / lineage / sufficiency)

Source: `app/evidence_intel/models.py`, `app/evidence_analytics/models.py`.

```mermaid
erDiagram
  EVIDENCE ||--o{ EVIDENCE_VERSION : "has versions"
  EVIDENCE ||--o| LINEAGE_GRAPH : "lineage"
  EVIDENCE ||--o| SUFFICIENCY_ASSESSMENT : "assessed"
  EVIDENCE ||--o| EVIDENCE_QUALITY_REPORT : "quality"
  EVIDENCE ||--o| EVIDENCE_TIMELINE : "timeline"

  EVIDENCE_VERSION {
    string evidence_id FK
    int    version_number
    string created_at
    string created_by
    string hash
    string previous_version
    string superseded_by
    string change_reason
    string evidence_status "Draft|Collected|Submitted|UnderReview|Approved|Rejected|Expired|Superseded"
  }
  LINEAGE_GRAPH {
    string evidence_id FK
    int    node_count
    int    edge_count
  }
  SUFFICIENCY_ASSESSMENT {
    string evidence_id FK
    string result
  }
  EVIDENCE_QUALITY_REPORT {
    string evidence_id FK
    list   dimensions
  }
  EVIDENCE_TIMELINE {
    string evidence_id FK
    list   events
  }
```

---

## 6. Audits

Source: `modules/governance/engines/audit_schedule_engine.py`,
`modules/governance/engines/governance_lifecycle_engine.py`, `ecs_state.operational_mock_audits`.
**[ASSUMPTION]** modeled from dict fields consumed in `module_capabilities.py`.

```mermaid
erDiagram
  AUDIT ||--o{ APPLICATION : covers
  AUDIT ||--o{ FRAMEWORK : assesses
  AUDIT ||--o{ OBSERVATION : raises
  AUDIT {
    string audit_id PK
    string framework FK
    string application FK
    string auditor
    int    days_remaining
    float  readiness_pct
    list   blockers
  }
```

---

## 7. AI SDLC Entities

Source: `modules/ai_sdlc/engines/ai_sdlc_workflow_engine.py`,
`modules/ai_sdlc/engines/ai_sdlc_governance_mock.py`.

```mermaid
erDiagram
  AI_APPLICATION ||--o{ SDLC_STAGE : "progresses through"
  SDLC_STAGE ||--o{ STAGE_ACTIVITY : contains
  SDLC_STAGE ||--o{ STAGE_ARTIFACT : requires
  STAGE_ACTIVITY ||--o{ AI_EVIDENCE : produces
  STAGE_ACTIVITY ||--o{ AI_FINDING : raises

  SDLC_STAGE {
    string stage_key PK "requirement|design|development|testing|go-live"
    string label
  }
  STAGE_ACTIVITY {
    string activity_id PK
    string stage_key FK
    string application
    string framework
    string status "Pending|In Review|Approved|Rejected|Needs Rework|Overdue|Awaiting Upload"
  }
  STAGE_ARTIFACT {
    string artifact_type PK
    string stage_key FK
  }
  AI_EVIDENCE {
    string evidence_id PK
    string application
    string framework
    string domain
    string control
    string artifact_type
    string due_date
    string status
    string stage
  }
  AI_FINDING {
    string finding_id PK
    string source
    string application
    string framework
    string domain
    string control
    string severity
    string owner
    string target_date
    string status
  }
```

---

## 8. Reports

Source: `modules/executive_overview/engines/reporting_module.py`.

```mermaid
erDiagram
  REPORT ||--o{ REPORT_OBSERVATION_ROW : includes
  REPORT ||--o{ EXPORT_RECORD : "exported as"
  REPORT {
    string id PK
    string title
    string description
    string format "PDF|Excel|PPT"
    string framework
    string application
    string owner
    string risk
    string category
    string schedule
    string status "Generated|Pending|Scheduled"
    string generated_at
    list   export_formats
  }
  REPORT_OBSERVATION_ROW {
    string observation_id PK
    string observation_title
    string framework FK
    string application
    string evidence_id FK
    string evidence_status
    string owner
    string generated_date
  }
  EXPORT_RECORD {
    string export_id PK
    string report_id FK
    string fmt "pdf|excel|csv"
    string generated_at
  }
```

---

## 9. Consolidated logical model (high level)

```mermaid
erDiagram
  AUTHENTICATED_USER ||--o{ ROLE : has
  ROLE ||--o{ APPLICATION : "scoped to"
  APPLICATION ||--o{ CONTROL : "implements (via framework)"
  FRAMEWORK ||--o{ CONTROL : contains
  CONTROL ||--o{ EVIDENCE : "evidenced by"
  CONTROL ||--o{ OBSERVATION : has
  CONTROL ||--o{ FINDING : has
  EVIDENCE ||--o{ EVIDENCE_VERSION : versions
  OBSERVATION ||--o| CLOSED_OBSERVATION : closed
  AUDIT ||--o{ OBSERVATION : raises
  AI_APPLICATION ||--o{ SDLC_STAGE : progresses
  SDLC_STAGE ||--o{ AI_EVIDENCE : produces
  REPORT ||--o{ REPORT_OBSERVATION_ROW : includes
  RISK ||--o| CONTROL : "linked_control"
  RISK {
    string risk_id PK
    string title
    string category
    string business_unit
    string application
    string owner
    string inherent_risk
    string residual_risk
    string status
    string linked_control FK
    string linked_framework FK
    int    aging_days
  }
```

Risk source: `modules/enterprise_grc/engines/grc_module_demo.py` (`_generate_risk_rows`).
