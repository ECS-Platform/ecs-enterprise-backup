# ECS Framework Coverage Audit (Phase 1)

**Mode:** READ-ONLY / ANALYSIS / REPORTING. **No code changes. No commits.** **Grounding:** `modules/frameworks/engines/framework_catalog.py` (`FRAMEWORK_CATALOG`, 15 frameworks / 305 controls), `config/environments/_base.yaml` (`framework_targets`, 13 entries), framework routes `/framework/{name}`, `framework_kpi_drill_engine`. Complements [Frameworks Library](README.md).

> **Two coverage dimensions:** (1) **Control catalog** — does a control set exist in `FRAMEWORK_CATALOG`? (2) **Target wiring** — is the framework mapped to execution target groups in `framework_targets`?

---

## 1. Coverage matrix (requested 10 frameworks)

| Framework | In `FRAMEWORK_CATALOG`? | In `framework_targets`? | Target groups | Coverage |
|---|---|---|---|---|
| **C-SITE** | ✅ (`CSITE`) | ✅ `csite` | os, db, middleware | **Full** |
| **DPSC** | ✅ `DPSC` | ✅ `dpsc` | db, appsec | **Full** |
| **PCI DSS** | ✅ `PCI DSS` | ✅ `pci_dss` | os, db, appsec | **Full** |
| **ITPP** | ✅ `ITPP` | ✅ `itpp` | os | **Full** |
| **ITDRM** | ✅ `ITDRM` | ✅ `itdrm` | os, db | **Full** |
| **VAPT** | ✅ `VAPT` | ✅ `vapt` | os, appsec | **Full** |
| **AppSec** | ✅ `AppSec` | ✅ `application_security` | appsec | **Full** |
| **OS Baseline** | ✅ `OS Baselining` | ✅ `os_baselining` | os | **Full** |
| **DB Baseline** | ✅ `DB Baselining` | ✅ `db_baselining` | db | **Full** |
| **Middleware Baseline** | ❌ **no catalog key** | ✅ `middleware_baselining` | middleware | **Partial** — target wired, **no control catalog** |

## 2. Full framework inventory (verified)

- **`FRAMEWORK_CATALOG` (15):** PCI DSS, DPSC, OS Baselining, DB Baselining, Nginx Baselining, AppSec, VAPT, CSITE, ITPP, ITDRM, SOC2, ISO27001, RBI Cyber Security, ISG, ASST.
- **`framework_targets` (13):** csite, pci_dss, dpsc, isg, mbss, asst, itpp, itdrm, os_baselining, db_baselining, middleware_baselining, application_security, vapt.

### Cross-coverage observations
- **Nginx Baselining**, **SOC2**, **ISO27001**, **RBI Cyber Security** have catalog controls but **no dedicated `framework_targets` entry** (Nginx is covered via os/middleware groups; SOC2/ISO/RBI are attestation/crosswalk frameworks, not query-target driven). **[Acceptable — not all frameworks are query-target driven.]**
- **`mbss` (Mobile Banking Security)** and **`middleware_baselining`** appear in `framework_targets` but **not** in `FRAMEWORK_CATALOG` → target-wired without a control set.

## 3. Gap classification

| ID | Finding | Severity | Recommendation (document only — DO NOT IMPLEMENT) |
|---|---|---|---|
| FC-P2-01 | Middleware Baseline has target wiring but no control catalog | **P2** | Add a `_middleware_catalog()` control set in a future, separately-approved change; today document via OS/DB baselining controls (see [Middleware Baselining](MIDDLEWARE_BASELINING.md)). |
| FC-P2-02 | `mbss` (Mobile Banking) target-wired, no catalog | **P2** | Same — document via DPSC/PCI/AppSec coverage ([Mobile Banking Security](MOBILE_BANKING_SECURITY.md)). |
| FC-P3-01 | Nginx/SOC2/ISO27001/RBI lack `framework_targets` entries | **P3** | Expected for attestation/edge frameworks; document rationale. |
| FC-P3-02 | Naming mismatch (catalog `CSITE` vs target `csite`; `OS Baselining` vs `os_baselining`) | **P3** | Document the canonical mapping table (above); no rename needed. |

## 4. Verdict
**Framework coverage: GO.** 9 of 10 requested frameworks have **full** catalog + target coverage; Middleware Baseline is **Partial** (target-wired, no control catalog) and documented via closest catalog coverage. All 15 catalog frameworks render at `/framework/{name}`. No framework code modified.

## Cross-references
- [Frameworks Library](README.md) · [Control Reference](../../01-product/product/ECS_CONTROL_REFERENCE_GUIDE.md) · [Predefined Query Readiness](../../03-development/operations/ECS_PREDEFINED_QUERY_READINESS_REPORT.md) · [Environment Framework Review](../../03-development/operations/ECS_ENVIRONMENT_FRAMEWORK_REVIEW.md)
