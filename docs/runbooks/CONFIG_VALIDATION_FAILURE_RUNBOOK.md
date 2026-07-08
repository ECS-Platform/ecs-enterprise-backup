# Runbook: Config Validation Failure

ECS refuses to start (or a deploy is blocked) due to environment configuration
validation errors.

> Reference: `config/config_validation.py`, `app/security_mode.py`
> · [`../operations/environment-configuration/00_ENVIRONMENT_CONFIGURATION_GUIDE.md`](../operations/environment-configuration/00_ENVIRONMENT_CONFIGURATION_GUIDE.md)
> · [`../operations/PROTOTYPE_DEMO_RUN_MODE.md`](../operations/PROTOTYPE_DEMO_RUN_MODE.md).

## Symptoms
- Startup aborts: `ECS environment '<env>' configuration is invalid: ...`
- CI `config-validation` workflow fails; `python -m config.config_validation` errors.

## Diagnose
1. Run the validator for the target env:
   `ECS_ENV=<env> python -m config.config_validation <env>` (add `--check-secrets`
   / `ECS_VALIDATE_SECRETS=1` to enforce secret presence).
2. Read the error list — each names the offending `config/environments/<env>.yaml`
   key (empty required field, localhost in a remote env, bad URL/port, missing
   target list, unresolved secret).

## Common causes & remediation
| Cause | Fix |
|-------|-----|
| Required field empty (e.g. `databases.postgres.*`) | Populate it in `config/environments/<env>.yaml`. |
| localhost/loopback in uat/prod/dr | Replace with the real remote host (no `127.0.0.1`). |
| Missing secret (strict env) | Provide it via env/Secret Manager (`*_env` pointer). |
| Empty `os_servers`/`db_servers` in strict env | Populate the target lists (or accept as UAT-planning warning). |
| Startup blocked in a prototype/demo | Set `ECS_SECURITY_MODE=demo` (or `ECS_STARTUP_FAIL_ON_CONFIG_ERROR=false`, or legacy `ECS_VALIDATE_CONFIG=off`) — demo is non-blocking. |

## Escape hatch by mode
- **demo/prototype:** config errors are **warnings** (non-blocking) by default.
- **uat:** non-blocking unless `ECS_STRICT_CONFIG_VALIDATION=true`.
- **prod/dr:** strict — errors abort startup (intended). Fix the config, don't bypass.

## Verify
- `python -m config.config_validation <env>` prints `PASS` (0 errors).
- App starts; startup log shows `Security mode:` and `Active environment:` lines.
