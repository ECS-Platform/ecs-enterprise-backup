# ECS Final Review Checklist

A pre-handoff / pre-merge review gate for the ECS Audit Intelligence closure work.
Every item is **verifiable with a command** and offline (no live systems, no
secrets, no bank IPs). Tick an item only after the command passes on a clean
checkout.

> Scope note: this checklist covers the **non-connector** closure (persistence,
> route smoke, demo/review pack). Enterprise connectors / Microsoft Graph are
> owned by a separate workstream and are intentionally **not** modified here.

---

## 1. Tests (scoped — do NOT run the full 2000+ suite)

```bash
PYTHONPATH=. pytest \
  tests/test_audit_persistence_foundation.py \
  tests/test_final_audit_route_smoke.py \
  tests/test_ecs_demo_smoke.py \
  tests/test_audit_intelligence_api.py \
  tests/test_audit_intelligence_ui.py
```

- [ ] All scoped tests pass (0 failed, 0 errors).
- [ ] `test_audit_persistence_foundation.py` runs against **both** the in-memory
      and in-memory-SQLite backends (no live DB).
- [ ] `test_final_audit_route_smoke.py` confirms every canonical API + UI route
      resolves (no 404) and aliases work.
- [ ] `test_ecs_demo_smoke.py` reports 10/10 checks.

## 2. Compile

```bash
python3 -m compileall modules/audit_intelligence scripts tests
```

- [ ] Exit code 0 (no `SyntaxError` / import-time failures in the compiled trees).

## 3. Routes (API)

Verified by `test_final_audit_route_smoke.py`; spot-check manually if desired:

- [ ] `/api/audit/dashboard` → 200, `{"ok": true, ...}`
- [ ] `/api/audit/assets` → 200 (paginated)
- [ ] `/api/audit/mapping` → 200
- [ ] `/api/audit/runs` → 200 (paginated)
- [ ] `/api/audit/repository` → 200 (alias of `/api/audit/evidence`)
- [ ] `/api/audit/observations` → 200 (paginated)
- [ ] `/api/audit/packs` → 200 (base: pack types + repo summary)
- [ ] `/api/audit/integrations` → 200 (masked config only)
- [ ] `/api/audit/health` → 200 (`status` ∈ {ok, degraded})
- [ ] Unknown route (`/api/audit/does-not-exist`) still 404s.

## 4. UI

- [ ] `/mvp/audit/dashboard` (alias) renders.
- [ ] `/mvp/audit/assets` renders.
- [ ] `/mvp/audit/technology-mapping` (alias) renders.
- [ ] `/mvp/audit/evidence-runs` (alias) renders.
- [ ] `/mvp/audit/validation-results` (alias) renders.
- [ ] `/mvp/audit/observations` renders.
- [ ] `/mvp/audit/repository` renders.
- [ ] `/mvp/audit/evidence-packs` (alias) renders.
- [ ] `/mvp/audit/executive-readiness` renders.
- [ ] Every page returns `text/html` with a non-trivial body (not an error stub).

## 5. APIs — safety & shape

- [ ] Success envelope: `{"ok": true, ...}`.
- [ ] Error envelope: `{"ok": false, "status": "error", "message": ..., "errors": [...]}`.
- [ ] Invalid query params (`?limit=abc`) return a bounded 200, not a 422/500.
- [ ] No stack traces or exception messages in any response body.

## 6. Docker

- [ ] `docker compose config` parses (compose file is valid).
- [ ] Demo/UAT compose is **not** required for the offline smoke path
      (`scripts/run_ecs_demo_smoke.py` runs with no Docker, no DB, no network).
- [ ] No connector/compose files were modified by this closure branch.

## 7. UAT placeholders

- [ ] `.env.example`, `config/environments/_base.yaml`, and
      `config/environments/uat.yaml` contain placeholders for every DB / infra /
      integration target (verified by `tests/test_uat_config_placeholders.py`).
- [ ] These files were **not** modified by this closure branch (owned by the
      UAT/connector workstream).

## 8. Secrets safety

```bash
PYTHONPATH=. pytest tests/test_final_audit_route_smoke.py -k secret -q
```

- [ ] No secret value ever appears in `/api/audit/integrations`,
      `/api/audit/integrations/health`, or `/api/audit/health` (SET/MISSING only).
- [ ] No hard-coded credentials/tokens/IPs added anywhere in this branch.

## 9. No `.DS_Store`

```bash
git ls-files | grep -c '\.DS_Store$'    # expect: 0
```

- [ ] `0` tracked `.DS_Store` files.
- [ ] `.DS_Store` is present in `.gitignore`.

## 10. No backup / unrelated artifacts

```bash
git status --porcelain --untracked-files=all
```

- [ ] No `docs/*.backup_*.xlsx` staged or committed.
- [ ] The NEEV workbook (`docs/ECS_LLM_TokenCalculation_Neev.xlsx`) and
      `scripts/enhance_neev_capacity_workbook.py` are **not** committed on this
      branch (they are a separate, unrelated artifact — see the final report).
- [ ] No temporary / editor / OS files committed.

## 11. Git status clean

```bash
git status -sb
```

- [ ] Working tree clean after commits (`nothing to commit`).
- [ ] Branch is `cursor/final-closure-review-pack`.
- [ ] Only intended files are in the branch's commits (persistence, route smoke,
      demo/review docs) — no connector / Graph / config files.

## 12. Demo smoke (final gate)

```bash
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py     # expect: 10/10 ALL PASS
```

- [ ] Prints `Result: 10/10 checks passed -> ALL PASS` (exit 0).

---

### Sign-off

| Reviewer | Role | Date | Result |
|----------|------|------|--------|
|          |      |      |        |
