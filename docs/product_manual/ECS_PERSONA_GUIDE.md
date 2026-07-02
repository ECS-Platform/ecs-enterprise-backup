# ECS Persona Guide

Part of the **ECS Product Operations Manual**. This chapter documents every persona/role ECS recognizes, grounded in `config/rbac.yaml`, `modules/shared/services/role_permissions.py`, `app/auth/` (enforcement, page guard, scope), and the `POST /login` routing in `app/main.py:334-399`.

## How roles work in ECS

ECS has **two role systems that coexist**:

1. **Legacy predicates (enforced today)** — `modules/shared/services/role_permissions.py`. The `can_*` functions gate what buttons/actions appear and are allowed. Roles are normalized via `normalize_role()` (aliases below).
2. **Canonical PolicyEngine catalog (target model)** — `config/rbac.yaml` `rbac_catalog`. Defines 22 fine-grained `verb.resource` permissions, dashboard page permissions, and scope per role. **Enforcement is flag-gated and OFF by default** (`RBAC_ENFORCEMENT_ENABLED`, `RBAC_PAGE_ENFORCEMENT_ENABLED`, `RBAC_SCOPE_FILTERING_ENABLED`, `RBAC_MUTATION_ENFORCEMENT_ENABLED`).

In **demo mode** (`DEMO_MODE=true`) all enforcement is bypassed — every persona can reach every screen, which is what makes ECS demo-friendly. The capabilities below describe the *intended* model.

### Legacy role normalization (`role_permissions.py:92-102`)

| Login/input role | Normalizes to |
|---|---|
| `compliance_officer`, `security_officer`, `framework_owner` | `compliance_head` |
| `operations_owner`, `ai_sdlc_owner` | `owner` |
| `ai_governance_owner` | `cio` |
| (blank/unknown) | `owner` (default) |

> **Known legacy quirk:** `security_officer` normalizes to `compliance_head`, so under legacy predicates it inherits compliance capabilities. The canonical catalog corrects this to read-only security analytics. Documented in `rbac_legacy_compat`.

### Scope dimensions (`rbac.yaml` `scope_filters` / `role_scope`)

| Scope | Meaning |
|---|---|
| `enterprise` | sees everything (no row filtering) |
| `vertical` | only the user's assigned vertical |
| `function` | only the user's assigned function |
| `application` | only assigned applications |
| `control` | only owned controls |

Demo scope (always active, `role_filter_scope.py`): owner = 3 apps, vertical_head = 5 apps, functional_head = 3 apps, compliance_head = 6 frameworks.

---

## Login personas (the 12 selectable on `/`)

From `login.html` + `POST /login`. Each row shows the demo user and the landing page.

| Persona | Login role | Demo user | Landing page |
|---|---|---|---|
| App Owner | `owner` | AppOwner | `/dashboard?role=owner` |
| Auditor | `auditor` | Auditor | `/dashboard?role=auditor` |
| CIO | `cio` | CIO | `/dashboard/cio` |
| Vertical Head | `vertical_head` | VerticalHead | `/dashboard/vertical-head` |
| Compliance Head | `compliance_head` | ComplianceOfficer | `/dashboard/compliance-head` |
| Compliance Officer | `compliance_officer` | ComplianceOfficer | `/dashboard/compliance-head` |
| Functional Head | `functional_head` | FunctionalHead | `/dashboard/functional-head` |
| Security Officer | `security_officer` | SecurityOfficer | `/dashboard/compliance-head` (shared template) |
| Operations Owner | `operations_owner` | OpsOwner | `/mvp/onboarding` |
| AI Governance Owner | `ai_governance_owner` | AIGovOwner | `/mvp/ai-governance` |
| AI SDLC Owner | `ai_sdlc_owner` | SDLCOwner | `/mvp/ai-sdlc` |
| Framework Owner | `framework_owner` | FrameworkOwner | `/mvp/framework-admin` |

Plus two non-login roles in the RBAC catalog: **System/Enterprise Admin** (`admin`/`enterprise_admin`/`system_admin`) and **Control Owner** (`control_owner`).

---

## Capability matrix (who can do what)

Derived from the `can_*` predicates in `role_permissions.py` and `framework_onboarding_engine.py`. ✅ = allowed, ❌ = not allowed.

| Action | Owner | Auditor | CIO | Vertical/Functional Head | Compliance/Security/Framework | Admin |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Upload / replace evidence | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Submit to auditor | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Review / approve / reject evidence | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Request re-upload | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Export reports | ✅ | ✅ | ✅ | ✅ (vertical) | ✅ (compliance) | ✅ |
| Manage / import frameworks | ❌ | ❌ | ✅ | ❌ | ✅ (compliance) | ✅ |
| Review framework onboarding | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Raise exception | ✅ | ✅ | ✅ | ✅ (vertical) | ✅ | ✅ |
| Approve / reject exception | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign owner | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Escalate | ✅ | ✅ | ✅ | ✅ (vertical) | ✅ | ✅ |
| Sync connectors (real) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| RAG reindex / warm | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

Predicate sources: `can_upload_evidence` (owner only, `role_permissions.py:130`), `can_review_evidence` (auditor/enterprise_admin, `:152`), `can_request_reupload` (auditor only, `:175`), `can_export_reports` (`:113`), `can_manage_frameworks`→`can_manage_framework_onboarding` (`framework_onboarding_engine.py:79`), `can_raise_exception` (`:105`), `can_assign_owner` (`:159`), `can_escalate` (`:167`), `can_admin_platform` (admins only, `:182`).

---

# Persona detail chapters

Each persona: who they are, what they see, what they cannot do, responsibilities, daily workflow, key dashboards, key reports, and the KPIs they care about.

---

## 1. Application Owner (`owner`)

**Who.** The accountable owner of one or more banking applications. The "doer" who collects and submits evidence. (Aliases that behave as owner: `operations_owner`, `ai_sdlc_owner`.)

**Scope.** Application — sees only assigned applications (3 in demo).

**Can see.** Main dashboard work queue, their frameworks, evidence health, bulk upload, completeness, search, evidence reuse, lifecycle, audit prep.

**Cannot do.** Review/approve/reject evidence; request re-upload; manage frameworks; approve exceptions; sync connectors; RAG admin.

**Responsibilities.** Keep assigned applications' control evidence current and approved; close gaps; respond to auditor clarification/re-upload requests.

**Daily workflow.** Open `/dashboard` → review "pending" and "resubmits required" queue → `/mvp/upload` or `/evidence/upload` to attach evidence → `/submit` to send to auditor → monitor `/mvp/evidence-health` for expiring/rejected items → close gaps via `/mvp/completeness` → `/mvp/workflow/upload-missing`.

**Key dashboards.** `/dashboard` (owner queue), `/mvp/evidence-health`, `/mvp/completeness`, `/mvp/upload`.

**Key reports.** Evidence Coverage, Stale Evidence Aging (export allowed).

**KPIs they care about.** Pending tasks, resubmits required, applications owned, owner open observations, owner SLA breaches, audit readiness % (owner strip, `demo_metrics.py`).

---

## 2. Auditor (`auditor`)

**Who.** Independent audit function. Read-only across the enterprise **plus** the authority to review and approve/reject evidence.

**Scope.** Enterprise.

**Can see.** Everything (read), the auditor review queue, audit prep, evidence approval analytics, all frameworks, search, reports.

**Cannot do.** Upload/submit/replace evidence (must request re-upload instead); manage/import frameworks; sync connectors; RAG admin.

**Responsibilities.** Review submitted evidence; approve or reject; request re-uploads/clarifications; close observations; run mock audits; assemble audit packages.

**Daily workflow.** `/dashboard` (auditor queue) → `/evidence/review` to approve/reject/clarify/request-reupload/close-observation → `/mvp/evidence-approval` for throughput → `/mvp/audit-prep` to prep upcoming audits and generate packages → `/mvp/workflow/mock-audit` to dry-run.

**Allowed actions** (`AUDITOR_ALLOWED_ACTIONS`, `role_permissions.py:83-89`): review, approve, reject, add_comment, request_reupload, assign_owner, reassign, escalate, transfer_review, view_trail, close_observation, clarify, close_gap, mock_audit, approve/reject reuse, approve/reject exception, export_summary, drill_down, escalate_stale, escalate_risk.

**Key dashboards.** `/dashboard` (auditor), `/mvp/audit-prep`, `/mvp/evidence-approval`, `/evidence/review`.

**Key reports.** Audit Readiness Scorecard, Rejection Analysis, Framework Validation, audit package export.

**KPIs they care about.** Auditor pending queue, approvals today, approval success %, rejection rate, avg validation time, audit readiness score.

---

## 3. CIO (`cio`)

**Who.** Executive accountable for enterprise technology governance posture. (Alias: `ai_governance_owner` behaves as CIO under legacy predicates.)

**Scope.** Enterprise.

**Can see.** CIO executive dashboard, enterprise analytics, heatmaps, trends, ROI, all frameworks (read), governance analytics.

**Cannot do.** Upload/submit evidence; auditor review/approve; request re-upload; sync connectors; RAG admin. (Executive read-only — `is_executive_readonly`.)

**Responsibilities.** Monitor enterprise readiness and risk; approve/raise exceptions; drive framework strategy (can manage frameworks); review framework onboarding; sponsor remediation.

**Daily workflow.** `/dashboard/cio` → drill enterprise KPIs → `/mvp/heatmaps` for hotspots → `/mvp/trends` for trajectory → `/mvp/roi` for value realization → `/workflow/leadership/review` to approve closures / send back / escalate to governance.

**Key dashboards.** `/dashboard/cio`, `/mvp/enterprise`, `/mvp/heatmaps`, `/mvp/roi`, `/mvp/demo-overview`.

**Key reports.** CIO Enterprise Governance Pack, Audit Readiness Scorecard, Pan-India Regional report.

**KPIs they care about.** Enterprise compliance %, evidence artefacts, audit completion %, enterprise readiness, open VAPT, AI hallucination alerts, regulator readiness.

---

## 4. Vertical Head (`vertical_head`)

**Who.** Leader accountable for a business vertical's compliance.

**Scope.** Vertical (5 apps in demo).

**Can see.** Vertical Head dashboard, comparison, enterprise view, frameworks (read), trends, reports for their vertical.

**Cannot do.** Upload/review evidence; manage frameworks; sync connectors. Executive read-only; can export, escalate, raise exceptions.

**Daily workflow.** `/dashboard/vertical-head` → `/mvp/comparison` to compare applications within the vertical → escalate elevated-risk apps → export vertical reports.

**Key dashboards.** `/dashboard/vertical-head`, `/mvp/comparison`, `/mvp/enterprise`.

**KPIs they care about.** National/vertical score, application maturity variance, open gaps, elevated-risk applications.

---

## 5. Compliance Head / Compliance Officer (`compliance_head` / `compliance_officer`)

**Who.** Owns framework & control compliance oversight. (Alias: `framework_owner` behaves as compliance_head under legacy predicates.)

**Scope.** Enterprise.

**Can see.** Compliance dashboard, all frameworks, control/framework coverage, completeness, reuse, lifecycle, evidence governance scorecards, reports.

**Cannot do.** Upload evidence; auditor review/approve; sync connectors. Can manage/import frameworks, export, raise exceptions, assign owner, review onboarding, make reuse decisions.

**Daily workflow.** `/dashboard/compliance-head` → `/mvp/platform/control-coverage` & `/framework-coverage` → `/mvp/completeness` to find gaps → `/mvp/framework-admin` to onboard/activate frameworks → `/mvp/reuse` for cross-framework reuse decisions → export compliance packs.

**Key dashboards.** `/dashboard/compliance-head`, `/mvp/completeness`, `/mvp/platform/control-coverage`, `/mvp/platform/framework-coverage`, `/mvp/framework-admin`.

**Key reports.** Cross-Framework Coverage Summary, Framework Validation, RBI Cyber Security Summary, regulatory packs.

**KPIs they care about.** Audit readiness %, control coverage %, framework maturity, open gaps, reuse %.

---

## 6. Security Officer (`security_officer`)

**Who.** CISO/security function — vulnerabilities, hotspots, findings.

**Scope.** Enterprise (canonical: read-only security analytics).

**Can see.** Shares the compliance-head dashboard template; security findings, VAPT, AppSec, heatmaps, frameworks (read).

**Cannot do (canonical).** Upload/review/approve evidence; manage frameworks; sync connectors. (Note legacy quirk: normalizes to `compliance_head` so legacy predicates over-grant; canonical catalog scopes it to `evidence.read`, `security.read`, `analytics.read`, `lineage.read`, `rag.read`.)

**Daily workflow.** Monitor `/framework/VAPT`, `/framework/AppSec`, `/framework/CSITE` → `/mvp/heatmaps` security hotspots → escalate critical vulns.

**KPIs they care about.** Critical vulns, VAPT open, MTTR days, security score (security strip, `demo_metrics.py`).

---

## 7. Functional Head (`functional_head`)

**Who.** Leader accountable for a business function's compliance.

**Scope.** Function (3 apps in demo).

**Can see.** Functional Head dashboard, frameworks (read), trends, reports for their function. Executive read-only; can export, escalate, raise exceptions.

**Cannot do.** Upload/review evidence; manage frameworks; sync connectors.

**Daily workflow.** `/dashboard/functional-head` → monitor function readiness → escalate gaps → export.

**KPIs they care about.** Function audit readiness %, open gaps, observations.

---

## 8. Operations Owner (`operations_owner`)

**Who.** Runs evidence-collection operations (scheduler, onboarding, connectors). Behaves as `owner` for permissions; distinct landing and focus.

**Scope.** Application.

**Can see.** Onboarding (landing), scheduler, integrations, integration health, evidence explorer, predefined queries, AI Ops Assistant.

**Daily workflow.** `/mvp/onboarding` → `/mvp/scheduler` to monitor collection jobs → `/mvp/integration-health` to check connectors → `/mvp/ai-ops-assistant` for incident investigation.

**KPIs they care about.** Collection jobs today, failed jobs, connector health %, evidence collected today, scheduler success rate.

---

## 9. AI Governance Owner (`ai_governance_owner`)

**Who.** Owns AI governance posture. Behaves as `cio` for permissions.

**Scope.** Enterprise.

**Can see.** AI Governance Posture (landing), AI Model & Prompt Registry, governance quality, AI SDLC.

**Daily workflow.** `/mvp/ai-governance` → review AI Compliance Score by dimension → `/mvp/ai-registry` for model/prompt governance → drill posture metrics.

**KPIs they care about.** AI Compliance Score, AI systems governed, prompt audits, hallucination rate, AI risk score.

---

## 10. AI SDLC Owner (`ai_sdlc_owner`)

**Who.** Owns the AI/SDLC governance gates. Behaves as `owner` for permissions.

**Scope.** Application.

**Can see.** AI SDLC home (landing), control tower, stage worklists, evidence collection, findings, reports.

**Daily workflow.** `/mvp/ai-sdlc` → `/control-tower` for readiness across frameworks×apps → step through stage worklists (Requirements → Go-Live) → `/findings` to remediate → `/reports`.

**KPIs they care about.** SDLC stage/release readiness, framework/control/evidence coverage %, stage gates passed, SAST findings open, release readiness %.

---

## 11. Framework Owner (`framework_owner`)

**Who.** Administers compliance frameworks. Behaves as `compliance_head` for permissions.

**Scope.** Enterprise.

**Can see.** Framework Administration (landing), framework loader, all frameworks, coverage screens.

**Daily workflow.** `/mvp/framework-admin` → import/onboard a framework via wizard → normalize controls → make reuse decisions → activate → review onboarding.

**KPIs they care about.** Frameworks owned, control coverage %, open gaps, onboarded/active/pending frameworks, controls imported.

---

## 12. Control Owner (`control_owner`)

**Who.** Owns specific controls' evidence. Not in the login dropdown; no dedicated dashboard (`pages: []`).

**Scope.** Control.

**Can do (canonical).** `evidence.read`, `evidence.collect`, `lineage.read`, `rag.read`.

**Cannot do.** Review/approve; export; manage frameworks; admin.

---

## 13. System / Enterprise / Platform Admin (`admin` / `enterprise_admin` / `system_admin`)

**Who.** Full platform administration. Not in the login dropdown.

**Scope.** Enterprise; permissions `*`, pages `*`.

**Can do.** Everything, including the admin-only mutations: connector sync (`POST /api/platform/sync/{connector}`, `/mvp/platform/sync-all`) and RAG reindex/warm (`/api/platform/rag/reindex`, `/mvp/ai-assistant/reindex`) — gated by `can_admin_platform` (`role_permissions.py:182`).

**Daily workflow.** `/mvp/integration-health` to sync connectors → `/mvp/platform/*` governance → `/mvp/ai-assistant` reindex → CMDB/correlation administration.

---

## Roles that are labels only (not wired to auth)

`governance_lead` and `platform_ops` appear as **KPI strip labels** in `demo_metrics.py` (e.g. governance score, open risks; platform uptime, active connectors) but have **no RBAC entry, no login option, and no `can_*` predicates**. Treat them as planned personas; in this build their dashboards are reached by passing the role as a query param in demo mode. `risk_manager` is not present in the repository.

---

See `ECS_FEATURE_REFERENCE.md` for the per-action detail, `ECS_USER_JOURNEYS.md` for end-to-end persona workflows, and `ECS_KPI_DICTIONARY.md` for the KPIs referenced above.
