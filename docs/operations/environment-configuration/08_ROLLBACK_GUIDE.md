# ECS Configuration / Deployment Rollback Guide

Because ECS is config-driven, most rollbacks are **configuration** rollbacks: no
rebuild, no code revert.

## 1. Config rollback (bad env value / endpoint)
Symptom: a config change (wrong host, disabled connector, bad flag) broke an env.

```bash
# Keep the previous env file / vault version under change control.
# Restore it, then restart:
cp .env.<env>.previous .env.<env>        # or restore the prior vault version
export ECS_ENV=<env>; set -a; source .env.<env>; set +a
python scripts/config_tools.py validate-<env> --check-secrets   # confirm PASS
# restart ECS
```

Confirm the restore with a diff against a known-good baseline:
```bash
python scripts/config_tools.py show-current-config <env>
python scripts/config_tools.py compare-envs <env> <lower-known-good>
```

## 2. Config-schema rollback (bad YAML change in git)
Symptom: a change to `config/environments/*.yaml` or `_base.yaml` broke loading.

```bash
git log --oneline -- config/environments/          # find the last good commit
git checkout <good-commit> -- config/environments/_base.yaml config/environments/<env>.yaml
python scripts/config_tools.py validate-all         # confirm PASS
```

## 3. Application artifact rollback
Symptom: a code/build regression (outside config).

- Redeploy the previous ECS image/tag. Config is external, so the previous artifact
  reads the same `.env.<env>` / vault — no config change needed to roll back code.

## 4. DR fail-back
See the DR Configuration Guide §Fail-back: switch `ECS_ENV=prod`, load `.env.prod`,
validate, restart.

## Rollback safety rules
- Always keep the **previous** `.env.<env>` (vault version) before changing it.
- Re-run `validate-<env> --check-secrets` after any rollback.
- Never roll back by hand-editing production secrets into git.
- Record the rollback (what/why/when) in the change log.

## Pre-change hygiene (makes rollback trivial)
```bash
# Snapshot the resolved profile BEFORE a change (secret-safe) for later comparison:
python scripts/config_tools.py show-current-config <env> --json > profile.<env>.before.json
```
