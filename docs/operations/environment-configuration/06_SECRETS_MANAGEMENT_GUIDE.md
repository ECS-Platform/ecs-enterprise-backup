# ECS Secrets Management Guide

## Principle
Secrets NEVER live in source or in committed YAML. YAML holds only the **name** of
the environment variable that supplies each secret (the `*_env` convention). At
runtime the value is read from the process environment (`.env.<env>` locally, or a
vault / K8s secret in real environments).

```yaml
databases:
  postgres:
    password_env: ECS_REPO_PG_PASSWORD    # NAME only — value comes from the env
```

## Where secrets come from (by environment)
| Env | Source |
|---|---|
| local | `.env` (git-ignored) |
| uat | `.env.uat` (git-ignored) or UAT vault |
| prod | Vault / K8s secret (preferred) or `.env.prod` (git-ignored) |
| dr | DR vault / K8s secret or `.env.dr` (git-ignored) |

## Masking
Secrets are ALWAYS masked in output:
- `config/config_validation.py::mask_secret` → `MISSING` or `ab****`.
- `config/deployment_profiles.py` → each secret field shows `SET` / `MISSING`.
- Integration diagnostics / `masked_config()` → `SET` / `MISSING`.
- `ECS_LOG_MASK_SECRETS=true` (default) keeps secrets out of logs.

Never print a raw secret; always route through these helpers.

## Validating secret presence (deploy gate)
```bash
# Structural (CI): secrets NOT required — missing ones are warnings.
python scripts/config_tools.py validate-config prod

# Deploy gate: run WITH the target env's secrets loaded; missing = errors.
export ECS_ENV=prod ; set -a; source .env.prod; set +a
python scripts/config_tools.py validate-prod --check-secrets
# (or ECS_VALIDATE_SECRETS=1 python -m config.config_validation prod)
```

## What must NEVER be committed
- `.env`, `.env.uat`, `.env.prod`, `.env.dr` (only the `*.example` / `*.template`
  files are tracked).
- Real hosts/IPs, passwords, API tokens, client secrets, access keys, certificates,
  kubeconfigs, connection strings with embedded credentials.
- Screenshots/logs containing any of the above.

Verify before every commit: `git status` shows no `.env.<env>`.

## Rotation
Rotate per bank policy by updating the value in the vault / `.env.<env>` — no code
or YAML change. Re-run the deploy-gate validation after rotation.
