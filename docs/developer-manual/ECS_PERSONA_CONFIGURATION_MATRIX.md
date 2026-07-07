# ECS Persona Configuration Matrix (Phase 3)

Confirms that environment configuration loads identically for **all ECS
personas**. Configuration is **persona-independent**: `get_environment_config()`
returns the same resolved configuration regardless of the logged-in role —
RBAC governs *what data a persona sees*, never *which environment endpoints ECS
connects to*. Therefore every persona inherits the active environment’s YAML
with no per-role configuration drift.

Personas are sourced from `config/rbac.yaml` (`rbac.roles` and
`rbac_catalog.roles`) plus the mandatory persona list. `Validation Status` =
result of loading the active environment while authenticated as that persona.

| Persona | RBAC role key | Accessible Modules (scope) | YAML Dependencies | Validation Status |
|---------|---------------|----------------------------|-------------------|-------------------|
| Admin | `admin` / `system_admin` | All modules (enterprise) | all sections | PASS |
| Executive | `cio` | Executive Overview, dashboards, analytics (enterprise) | applications, reporting | PASS |
| CIO | `cio` | Executive Overview, Governance, analytics (enterprise) | applications, reporting, llm | PASS |
| CISO | `security_officer` | Security findings, Risk, Governance (enterprise) | connectors (security), predefined_query_targets (appsec) | PASS |
| Auditor | `auditor` | Audit Prep, Evidence review/export, Frameworks (enterprise) | databases.postgres, storage, reporting | PASS |
| Audit Manager | `auditor` | Audit Prep, Evidence review, Reports (enterprise) | databases.postgres, reporting | PASS |
| Governance Owner | `compliance_officer` | Governance, Compliance, Frameworks (enterprise) | framework_targets, databases.postgres | PASS |
| Compliance Owner | `compliance_officer` | Compliance, Frameworks, Evidence (enterprise) | framework_targets, connectors | PASS |
| Risk Owner | `security_officer` / `cio` | Risk, Findings, Remediation (enterprise) | predefined_query_targets, framework_targets | PASS |
| Framework Owner | `compliance_officer` (legacy alias `compliance_head`) | Frameworks, Control Management | framework_targets, predefined_query_targets | PASS |
| Control Owner | `control_owner` | Control Management, Evidence (control scope) | predefined_query_targets, databases.postgres | PASS |
| Evidence Owner | `application_owner` | Evidence Collection/Repository (application scope) | connectors, storage, databases.postgres | PASS |
| Application Owner | `application_owner` | Application Inventory, Evidence (application scope) | applications, connectors | PASS |
| Operations Owner | `application_owner` (legacy alias `owner`) | Operations, Scheduler, Integrations Health | connectors, predefined_query_targets | PASS |
| AI Governance Owner | `cio` (legacy alias) | AI Governance (Model/Prompt Registry, Posture) | llm | PASS |
| AI SDLC Owner | `application_owner` (legacy alias `owner`) | AI SDLC (Requirements → Prod Monitoring) | static/demo (no env endpoints) | PASS |
| Reviewer | `auditor` | Evidence review (enterprise) | databases.postgres | PASS |
| Approver | `auditor` / `compliance_officer` | Evidence approval, Exception governance | databases.postgres | PASS |
| Read-Only User | `cio` (read scope) / `control_owner` | Dashboards (read-only) | read-only over all sections | PASS |
| Vertical Head | `vertical_head` | Aggregated evidence/analytics (vertical scope) | applications, reporting | PASS |
| Functional Head | `functional_head` | Aggregated evidence/analytics (function scope) | applications, reporting | PASS |

## Discovery sources checked

* **RBAC**: `config/rbac.yaml` → `rbac.roles`, `rbac_catalog.roles`,
  `rbac_legacy_compat` aliases.
* **Persona registry / authorization framework**: `app/auth/` and
  `modules/shared/services/module_capabilities.py` / `module_workspace.py`.
* **Navigation / workspace config**: persona-driven navigation is filtered by
  RBAC permissions; it consumes the same environment configuration.

## Conclusion

Configuration loading is **uniform across all personas** — there is no
per-persona configuration path. Validation passes for every persona against the
active environment.
