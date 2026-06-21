# Unsupported Technology KPI — Validation

**KPI:** "Unsupported Tech" on the Predefined Queries page.
**Backend:** `predefined_queries_engine` — a control is "unsupported" when it is predefined but `detect_technology(query) == "Unknown"`. The same condition appends `"Unsupported technology for <id>"` to `validation_report["errors_found"]` during `load_predefined_queries()`.
**Drilldown:** `drill_predefined_query_kpi("unsupported_tech")`.

## Reconciliation (KPI == backend findings == drilldown)

| Source | Count |
|---|---|
| KPI displayed value | **21** |
| Backend `errors_found` "Unsupported technology …" entries | **21** |
| Drilldown row count | **21** |
| **All equal** | ✅ |

This directly satisfies the requirement *"Unsupported Technology KPI equals backend findings."* The startup log lines the user observed (`Unsupported technology: DB-005, DB-006, DB-007, OS-001, OS-004 …`) are the same 21 records.

## The 21 unsupported controls (with reason)

All 21 share the same deterministic reason: **the query text matched no `TECHNOLOGY_RULES` pattern**, so `detect_technology()` returned `Unknown` and no connector can run it.

`DB-005, DB-006, DB-007, OS-001, OS-004, OS-005, MW-002, MW-003, PCI-002, PCI-004, APP-003, DPSC-001, DPSC-002, VAPT-001, VAPT-002, VAPT-003, ITPP-001, ITPP-004, AI-001, AI-002, AI-003`

## Drilldown improvements (this pass)

The Unsupported Technology drilldown now returns **traceable** columns:

| Column | Meaning |
|---|---|
| `control` | Control ID |
| `control_name` | Control name |
| `framework` | Framework coverage |
| `query_excerpt` | First 60 chars of the actual query (shows *why* detection failed) |
| `reason` | "Query text did not match any known technology pattern, so no connector can run it." |

No synthetic rows; empty-state (`note`) is returned if the set is ever empty.

## Special note — OS-001

OS-001 is `Unknown` technology (correctly counted here) **and** was previously in `LIVE_CONTROL_IDS`, which had enabled its Run button — a contradiction now fixed (`is_live_execution_enabled` requires executable capability). See `ECS_FALSE_READY_AUDIT.md`. OS-001 now consistently shows **Unsupported Technology** with no Run action.

## Technology mapping reference

`detect_technology()` matches (case-insensitive substring) against `TECHNOLOGY_RULES`:

| Technology | Example patterns |
|---|---|
| GitLeaks | `gitleaks detect`, `gitleaks` |
| Trivy | `trivy image`, `trivy` |
| SonarQube | `/api/issues/search`, `sonarqube` |
| NGINX | `nginx -t`, `nginx -T` |
| PostgreSQL | `pg_stat_replication`, `show ssl`, `from pg_`, `pg_` |
| Oracle | `dba_role_privs`, `v$encryption_wallet`, `v$`, `dba_` |
| Windows | `get-hotfix`, `get-mpcomputerstatus`, `powershell` |
| Linux | `df -h`, `free -m`, `timedatectl`, `/etc/ssh`, `systemctl status` |

A query whose text contains none of these resolves to `Unknown` → Unsupported Technology. To make any of the 21 executable, its query must be mapped to a known technology (a content/Excel task) and a connector must exist for that technology.

## Verdict

✅ **Unsupported Technology KPI is trustable** — count, backend findings, and drilldown reconcile exactly, and each row carries an explainable reason.
