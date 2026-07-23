# ECS Module Migration — Rollback Report

**Date:** 2026-06-01  
**Migration commit target:** Module-oriented refactor (engines, templates, routes)

## Rollback Strategy

The migration preserves backward compatibility via `app/*.py` shims. Rollback can be performed at three levels depending on severity.

### Level 1 — Revert commit (recommended)

If the migration was committed as a single changeset:

```bash
git revert <migration-commit-sha>
```

This restores prior `app/` monolith files and removes `modules/` moves while keeping git history intact.

### Level 2 — Restore route shims only

If route relocation causes import issues but engines remain in `modules/`:

1. Copy route implementations back from `modules/*/routes/` to `app/`:
   - `modules/ai_sdlc/routes/routes_ai_sdlc_governance.py` → `app/routes_ai_sdlc_governance.py`
   - `modules/enterprise_grc/routes/routes_grc_demo.py` → `app/routes_grc_demo.py`
   - `modules/shared/routes/evidence_routes.py` → `app/evidence_routes.py`
   - `modules/shared/routes/routes_mvp.py` → `app/routes_mvp.py`
2. Remove shim re-exports from those four `app/` files.
3. Restart the application.

### Level 3 — Full monolith restore (pre-modules)

To fully undo the modular layout:

```bash
git checkout <pre-migration-sha> -- app/
git checkout <pre-migration-sha> -- templates/   # if templates were moved
rm -rf modules/
```

Then restore `app/main.py` Jinja loader to single `templates/` directory if changed.

## Files Changed in Migration

| Category | Count | Rollback action |
|----------|-------|-----------------|
| Engine Python files moved to `modules/` | 99 | Restore to `app/` or keep shims |
| Template files moved to `modules/*/templates/` | 149 | Restore to `templates/` |
| Route files moved to `modules/*/routes/` | 4 | Restore to `app/` |
| Compatibility shims in `app/` | 102 | Delete shims; restore originals |
| Import rewrites | ~100 files | Revert via git |

## Route Shim Map (current)

| Shim (`app/`) | Canonical location |
|---------------|-------------------|
| `routes_mvp.py` | `modules/shared/routes/routes_mvp.py` |
| `evidence_routes.py` | `modules/shared/routes/evidence_routes.py` |
| `routes_ai_sdlc_governance.py` | `modules/ai_sdlc/routes/routes_ai_sdlc_governance.py` |
| `routes_grc_demo.py` | `modules/enterprise_grc/routes/routes_grc_demo.py` |
| `main.py` | Stays in `app/` (bootstrap) |

## Validation After Rollback

Run these commands to confirm rollback success:

```bash
PYTHONPATH=. python3.12 scripts/validate_post_migration.py
PYTHONPATH=. python3.12 -c "
import importlib.util, glob, sys
failed = 0
for p in glob.glob('tests/test_*.py'):
    spec = importlib.util.spec_from_file_location('t', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for n in dir(m):
        if n.startswith('test_'):
            try: getattr(m, n)()
            except Exception: failed += 1
sys.exit(failed)
"
```

Expected: validation script reports 0 failures; critical test suites pass.

## Known Non-Blocking Test

- `tests/test_ai_sdlc_redesign.py::test_sidebar_new_menu_only` — pre-existing failure unrelated to module migration.

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Broken imports via shims | All shims use explicit `from modules.X import *` |
| Template not found | `ChoiceLoader` in `app/main.py` scans all module template dirs |
| URL regression | No route paths changed; only file locations |
| Mock data drift | Engines moved verbatim; no logic changes |

## Contact / Ownership

See `docs/03-development/developer-manual/ECS_MODULE_OWNERSHIP.md` for module ownership after rollback planning.
