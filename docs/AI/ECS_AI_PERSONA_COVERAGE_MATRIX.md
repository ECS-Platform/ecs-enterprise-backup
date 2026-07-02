# ECS AI Persona & Login Coverage Matrix (Phase 4)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`
**Sources:** `app/auth/roles.py` (9 canonical roles), `modules/executive_overview/templates/login.html`
(12 login roles), `modules/shared/services/persona_display.py` (12 personas + tabs),
`config/rbac.yaml`, `scripts/role_route_matrix_certification.py` (test identities).

**Key fact for this assessment:** AI behavior in ECS is **not role-conditional at the provider layer**.
The LLM provider is global (`get_provider()`), selected by config, defaulting to **local Ollama**.
Therefore **every persona/login is local-LLM ready** — RBAC governs *what data/pages* a persona sees,
not *which model* serves it.

---

## 1. Canonical roles (authoritative — 9)

`app/auth/roles.py:36-64`: `cio`, `auditor`, `application_owner`, `compliance_officer`,
`security_officer`, `vertical_head`, `functional_head`, `control_owner`, `system_admin`.
Default role: `application_owner` (`roles.py:77-79`).

## 2. Login-selectable roles (12)

`login.html:24-37`: `owner`, `auditor`, `cio`, `vertical_head`, `compliance_head`,
`compliance_officer`, `functional_head`, `security_officer`, `operations_owner`,
`ai_governance_owner`, `ai_sdlc_owner`, `framework_owner`.

## 3. Persona registry + dashboard tabs (12)

`persona_display.py` `PERSONA_BY_ROLE` (display names) and `PERSONA_TABS` (per-role dashboard tabs).
Unknown roles fall back to CIO tabs (`persona_display.py:206`).

---

## 4. Requested Persona → Actual Role → Login → AI Readiness

| Requested persona | Real role mapping | Login path? | AI/LLM access | Local-LLM ready |
|---|---|---|---|---|
| **Admin** | `admin`/`enterprise_admin` → canonical `system_admin` (`roles.py:61-63`); dev principal default `admin` (`auth.yaml:61`) | Not on picker; via dev-mode / direct | Full (incl. platform sync/RAG admin: `role_permissions.py:182-189`) | ✅ |
| **Executive** | Conceptual `category="executive"` (cio/vertical_head/functional_head) — not a distinct role | via those roles | Assistant/RAG read | ✅ |
| **CIO** | `cio` (real) | `/dashboard/cio` (`app/main.py:338-342`) | Assistant/RAG, AI-gov UI | ✅ |
| **CISO** | Not a role; string `ciso` is a metric alias for `security_officer` (`demo_metrics.py:200`) | via `security_officer` | Assistant/RAG read | ✅ (via security_officer) |
| **Auditor** | `auditor` (real) | `/dashboard` (`app/main.py:393-398`) | Assistant/RAG read; evidence review | ✅ |
| **Audit Manager** | **Not present** | — | — | ❌ (no role) |
| **Governance Owner** | Not a role; `governance_lead`/`governance_team` are demo metric keys (`demo_metrics.py:232`) | — | — | ❌ (no role) |
| **Compliance Owner** | `compliance_head`/`compliance_officer` → canonical `compliance_officer` | `/dashboard/compliance-head` (`app/main.py:350-354`) | Assistant/RAG read | ✅ |
| **Risk Owner** | Not a role; `risk_team` demo metric key | — | — | ❌ (no role; covered by security/compliance) |
| **Framework Owner** | `framework_owner` → canonical `compliance_officer` (distinct persona/tabs) | `/mvp/framework-admin` (`app/main.py:386-390`) | Assistant/RAG read | ✅ |
| **Control Owner** | `control_owner` canonical (`roles.py:59`); **not on login**; empty page list in catalog | direct only | Provider-global | ✅ (role exists) |
| **Evidence Owner** | Not a role; `evidence_owner` is a mock record field (`ecs_mock_engine.py:615`) | — | — | ❌ (no role) |
| **Application Owner** | `owner` → canonical `application_owner` | `/dashboard` (`app/main.py:393-398`) | Assistant/RAG; upload/submit | ✅ |
| **Operations Owner** | `operations_owner` → canonical `application_owner` (distinct landing) | `/mvp/onboarding` (`app/main.py:368-372`) | Ops assistant (deterministic) + RAG | ✅ |
| **AI Governance Owner** | `ai_governance_owner` → canonical `cio` | `/mvp/ai-governance` (`app/main.py:374-378`) | AI-gov UI (mock) + RAG | ✅ |
| **AI SDLC Owner** | `ai_sdlc_owner` → canonical `application_owner` | `/mvp/ai-sdlc` (`app/main.py:380-384`) | AI SDLC UI (mock) + RAG | ✅ |
| **Reviewer** | Not a role; `reviewer` is a workflow/mock field | — | — | ❌ (capability, not role) |
| **Approver** | Not a role; `approving_authority`/`approved_by` fields | — | — | ❌ (capability, not role) |
| **Read-Only User** | Behavior via `is_executive_readonly()` (`role_permissions.py:148-149`); auditors read-only for upload | via exec roles | Assistant/RAG read-only | ✅ (behavior, not role) |

---

## 5. Logins assessed (every login path)

| Login role string | Landing | Source | Local-LLM ready |
|---|---|---|---|
| cio | `/dashboard/cio` | `app/main.py:338` | ✅ |
| vertical_head | `/dashboard/vertical-head` | `:344` | ✅ |
| compliance_head / compliance_officer | `/dashboard/compliance-head` | `:350` | ✅ |
| functional_head | `/dashboard/functional-head` | `:356` | ✅ |
| security_officer | `/dashboard/compliance-head` | `:362` | ✅ |
| operations_owner | `/mvp/onboarding` | `:368` | ✅ |
| ai_governance_owner | `/mvp/ai-governance` | `:374` | ✅ |
| ai_sdlc_owner | `/mvp/ai-sdlc` | `:380` | ✅ |
| framework_owner | `/mvp/framework-admin` | `:386` | ✅ |
| owner | `/dashboard` | `:393` | ✅ |
| auditor (and other) | `/dashboard` | `:393` | ✅ |
| dev principal (`admin`) | env/dev-mode | `auth.yaml:53-61` | ✅ |

---

## 6. Findings / Gaps (personas requested but not real roles)

Requested-but-absent as distinct roles: **Audit Manager, Governance Owner, Risk Owner, Evidence
Owner, Reviewer, Approver**. These exist only as *capabilities*, *mock fields*, or *metric profiles*,
not as login roles. **None of these gaps affect local-LLM readiness** — they are RBAC modeling gaps.
Recommendation (out of scope here): if these personas are required for the program, add them as
canonical roles + aliases in `app/auth/roles.py` and login options; AI access requires no change.

## 7. Conclusion

**100% of real ECS logins/personas are local-LLM ready.** AI serving is provider-global and defaults
to local Ollama, so persona coverage is a function of RBAC (data/page scope), all of which operates
unchanged under a local model. The only gaps are *missing role definitions*, not AI gaps.
