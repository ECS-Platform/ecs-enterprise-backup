# ECS Predefined Query Readiness Report (Phase 1)

**Mode:** READ-ONLY / ANALYSIS / REPORTING. **No code changes. No commits.** **Grounding:** `modules/operations/engines/predefined_queries_engine.py`, `predefined_query_audit.py`, `predefined_query_evidence.py`, `query_connectors.py` (interfaces only), `config/environments/_base.yaml` (`framework_targets`, `predefined_query_targets`), `ECS_Query_Driven_Control_Library_Consolidated.xlsx`. Complements [Predefined Query Architecture](ECS_PREDEFINED_QUERY_ARCHITECTURE.md).

---

## 1. Pipeline readiness

```
Framework → Control → Query → (detect tech) → Connector → Target → Execution → Parsing → Evidence → Repository → Workflow → Dashboard
```

| Stage | Implementation | Readiness |
|---|---|---|
| Framework mapping | `framework_targets` in env config (csite, pci_dss, dpsc, isg, mbss, asst, itpp, itdrm, os/db/middleware baselining, appsec, vapt) → target groups | ✅ Implemented |
| Control mapping | control library Excel → controls; `predefined = bool(query)` | ✅ Implemented |
| Query → technology | `detect_technology()` via `TECH_SIGNATURES` (deterministic, no AI) | ✅ Implemented |
| Connector/target resolution | `build_connector_config()` from env layer + static fallback | ✅ Implemented |
| **Execution** | `query_connectors.py` = **interfaces only, no runtime** | ⚠ **Partial** |
| Parsing | audit/evidence helper modules present | ✅ Implemented (logic), pending live exec |
| Evidence → repository | `predefined_query_evidence` → evidence rows | ✅ Implemented |
| Workflow → dashboard | counts (controls/queries/manual/unsupported) on `/mvp/predefined-queries` | ✅ Implemented |

## 2. Target coverage

| Target | Detection | Execution runtime | Readiness |
|---|---|---|---|
| PostgreSQL | ✅ allow-listed read-only queries | ❌ interface-only | Partial |
| Linux | ✅ | ❌ | Partial |
| Nginx | ✅ (`nginx -t/-T`) | ❌ | Partial |
| Oracle | ✅ (`dba_*`, `v$*`) | ❌ | Partial |
| Windows | ✅ (PowerShell) | ❌ | Partial |
| SonarQube | ✅ (`/api/issues/search`) | ❌ (query path); source connector exists separately | Partial |
| Trivy | ✅ | ❌ | Partial |
| Gitleaks | ✅ | ❌ | Partial |
| MySQL / SQL Server / Tomcat / Application | ❌ not in `TECH_SIGNATURES` | ❌ | Future |

## 3. Safety controls (validated)
- **PostgreSQL allow-list** (`ALLOWED_POSTGRESQL_QUERIES`, `_normalize_query_allowlist`) — read-only checks only; no arbitrary SQL.
- `_connector_config_loaded()` gates live execution; demo mode reports deterministically without executing.
- Undetectable-technology queries counted as **manual/unsupported** (not silently passed).

## 4. Gap classification

| ID | Finding | Severity | Recommendation (document only — DO NOT IMPLEMENT) |
|---|---|---|---|
| PQ-P2-01 | Execution runtime not implemented (interfaces only) | **P2** | Build execution adapters in a future, separately-approved phase; until then demo/UAT uses deterministic reporting. |
| PQ-P2-02 | Target server lists empty by default in env config | **P2** | Populate `os/db/middleware/appsec` lists per env at deploy time (config, not code). |
| PQ-P3-01 | MySQL/SQL Server/Tomcat/Application not in `TECH_SIGNATURES` | **P3** | Document as Future targets; add signatures in a future change. |

## 5. Verdict
**Predefined-query layer: PARTIAL — GO for demo/UAT reporting, NOT for live execution.** Framework/control mapping, technology detection, parsing, evidence generation, and dashboards are implemented; **live query execution against targets is intentionally interface-only** and must be built in a future, separately-approved phase. No code modified here.

## Cross-references
- [Predefined Query Architecture](ECS_PREDEFINED_QUERY_ARCHITECTURE.md) · [Predefined Query Execution Guide](ECS_PREDEFINED_QUERY_EXECUTION_GUIDE.md) · [Connector Readiness](ECS_CONNECTOR_READINESS_REPORT.md) · [Workflow Validation](../../04-testing/testing/ECS_WORKFLOW_VALIDATION_REPORT.md)
