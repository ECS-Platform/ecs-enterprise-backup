# ECS Deployment Configuration Guide

How the ECS configuration framework resolves settings per environment, and how to
operate it.

## Resolution order (highest wins)

1. **Process environment variable** (`ECS_*`, from `.env.<env>` / vault / K8s).
2. **`config/environments/<ECS_ENV>.yaml`** override for the active environment.
3. **`config/environments/_base.yaml`** schema-complete defaults.
4. Built-in fallback in the `${VAR:-default}` placeholder.

Loader: `config/environment_loader.py` (`get_environment_config`, typed accessors).
Substitution engine: `ecs_platform/config/loader.py` (`${VAR}` / `${VAR:-default}`,
bool/int coercion). Validator: `config/config_validation.py`. Profiles:
`config/deployment_profiles.py`.

## Deployment sections (all env-var driven)

`application`, `databases`, `redis`, `caching`, `storage`, `vector_store`, `llm`,
`scheduler`, `connector_execution`, `connectors.*`, `security`, `authentication`,
`logging`, `monitoring`, `reporting`, `extensions`, `predefined_query_targets`.

See `_base.yaml` for the full schema and every `${VAR}` name.

## Operating commands

```bash
python scripts/config_tools.py validate-config <env>        # structural
python scripts/config_tools.py validate-<uat|prod|dr> --check-secrets   # deploy gate
python scripts/config_tools.py show-current-config <env>    # secret-safe profile
python scripts/config_tools.py compare-envs <a> <b>         # field-level diff
python scripts/config_tools.py generate-env-template <env>  # scaffold .env
python -m config.deployment_profiles --all                  # all profiles
```

## Adding a new environment

1. Add `config/environments/<name>.yaml` (override only what differs from base).
2. Add `<name>` to `VALID_ENVIRONMENTS` in `config/environment_loader.py`.
3. (If it is a remote tier) add it to `_STRICT_ENVS` / `_NO_LOCALHOST_ENVS` in
   `config/config_validation.py`.
4. `python scripts/config_tools.py validate-config <name>`.

No other code changes are required.

## CI

`.github/workflows/config-validation.yml` runs `validate-all` and asserts prod/dr
contain no localhost — see the workflow for the exact gate.
