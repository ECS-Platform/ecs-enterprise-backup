# ECS "False Ready" Audit

**Objective:** Find every place ECS displays an affirmative-capability word (Ready / Available / Operational / Configured / Enabled) and verify runtime reality supports it. Replace any unsupported claim with a precise state.

**Rule:** *Ready* must mean **connector exists · dependency installed · configuration exists · target configured · query executable.** If not, show **Configuration Required / Connector Missing / Dependency Missing / Target Not Configured**.

## Finding 1 — Predefined Queries "Ready" was cosmetic (FIXED)

**Before:** `_derive_status()` returned **Ready** for any predefined control with a detected technology — **16 of 37** controls. This ignored whether a connector was implemented, whether the control was wired for live execution, and whether the driver was installed.

**Runtime reality (verified):** only **6** controls are genuinely executable.

| control_id | technology | Truthful status | Executable | Why |
|---|---|---|---|---|
| DB-001, DB-002, DB-003 | PostgreSQL | **Ready** | ✅ | Implemented connector + live + `psycopg2` present |
| OS-002 | Linux | **Ready** | ✅ | Implemented connector + live |
| APP-001 | SonarQube | **Ready** | ✅ | Implemented connector + live |
| APP-002 | GitLeaks | **Ready** | ✅ | Implemented connector + live |
| OS-003, ITPP-002, ITPP-003 | Linux | **Configuration Required** | ❌ | Connector implemented but control not wired for live execution |
| APP-004 | Trivy | **Configuration Required** | ❌ | Connector implemented but control not wired for live execution |
| DB-004, PCI-003 | Oracle | **Connector Missing** | ❌ | `DatabaseConnector.connect()` raises `NotImplementedError` |
| OS-006, OS-007, PCI-001 | Windows | **Connector Missing** | ❌ | `SSHConnector.connect()` raises `NotImplementedError` |
| MW-001 | NGINX | **Connector Missing** | ❌ | `SSHConnector.connect()` raises `NotImplementedError` |

**After:** truthful distribution — **Ready 6 · Configuration Required 4 · Connector Missing 6 · Unsupported Technology 21 · Manual 0**.

**Fix:** `assess_execution_capability()` (new) is the single source of truth; `_derive_status()` delegates to it; control records carry `executable` + `capability_reason`; badges show the precise status with a tooltip.

## Finding 2 — "Run Query" enabled on a non-executable control (FIXED)

**OS-001** was in `LIVE_CONTROL_IDS` (so `is_live_execution_enabled` returned True and the Run button was enabled) **but its technology is `Unknown`** → status "Unsupported Technology". Clicking Run could only fail.

**Fix:** `is_live_execution_enabled()` now also requires `assess_execution_capability().executable`. OS-001 (and any non-Ready control) no longer offers Run. Verified: `is_live_execution_enabled(OS-001) == False`; the detail page renders no Run form.

## Finding 3 — Dependency-dependent "Ready" (FIXED, environment-aware)

PostgreSQL controls (DB-001/2/3) require `psycopg2`. If the driver is absent, they now report **Dependency Missing** (via `_dependency_available()` → `importlib.util.find_spec`) rather than "Ready", and live execution additionally degrades to a graceful structured error (`connector_unavailable`) instead of a 500. In the current environment `psycopg2` **is** installed, so these correctly show **Ready**.

## Finding 4 — Dead references in the live set (DOCUMENTED)

`LIVE_CONTROL_IDS` contains **APPSEC-001** and **APPSEC-002**, which are **not present** in `ECS_Query_Driven_Control_Library_Consolidated.xlsx`. No UI impact (no rows), but they are misleading constants. Recommend pruning in a future content pass; left unchanged here to avoid altering the curated live set during a trustability fix.

## Other affirmative-capability words reviewed

| Word | Location | Backed by runtime? | Action |
|---|---|---|---|
| "Live demo execution via … connector" | Detail Summary (when executable) | Yes — only shown when `execution_prep.execution_enabled` (now capability-gated) | No change needed |
| "Connector Configuration Loaded" | Startup validation log | Reflects `CONNECTOR_CONFIG` truthiness | Accurate; informational |
| Audit Readiness "Ready" band | Dashboards | Score-band, deterministic | Out of scope (different concept); accurate |

## Net result

No predefined-query "Ready" state now exists without genuine executable capability. Every non-executable control carries an explicit, explainable reason.
