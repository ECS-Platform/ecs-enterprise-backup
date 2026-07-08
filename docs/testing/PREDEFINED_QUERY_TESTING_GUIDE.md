# ECS Predefined Query — Testing Guide

How to test the predefined-query module: catalog integrity, target configs,
Docker test targets, and mock/dry-run execution. All offline unless you
explicitly bring up Docker targets.

---

## 1. Test suites

| Test file | Covers |
|---|---|
| `tests/test_predefined_db_connectors.py` | DB config, supplementary DB catalog, allow-lists, routing, mocked execution |
| `tests/test_predefined_infra_queries.py` | Oracle/NGINX/Linux/RHEL8/9 catalog, capability, shell dispatch |
| `tests/test_predefined_extended_technology_queries.py` | Redis/Apache/Tomcat/SQL Server/Mongo/K8s/OpenShift; **total = 187** |
| `tests/test_predefined_extended_connectors.py` | Extended routing, mocks, graceful failures |
| `tests/test_predefined_db_frontend.py` | UI/API: visibility, search/filter, Run Query routing |
| `tests/test_predefined_docker_targets.py` / `..._extended_docker_targets.py` | `docker-compose.yml` services + profile gating |
| `tests/test_predefined_*_diagnostic.py` | the `check_predefined_*` environment scripts |
| `tests/test_predefined_query_targets_and_catalog.py` | **(this wave)** catalog integrity, target registries, localhost policy, PQ compose profiles, runner |

## 2. Run the tests

```bash
export DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off
PYTHONPATH=. pytest -q -p no:cacheprovider \
  tests/test_predefined_query_targets_and_catalog.py \
  tests/test_predefined_db_connectors.py \
  tests/test_predefined_infra_queries.py \
  tests/test_predefined_extended_technology_queries.py \
  tests/test_predefined_extended_connectors.py

python -m compileall modules app scripts tests config
```

## 3. The runner (offline, no live systems)

```bash
python scripts/run_predefined_query_tests.py summary            # catalog + registry summary
python scripts/run_predefined_query_tests.py inventory          # regenerate the inventory doc
python scripts/run_predefined_query_tests.py validate-targets --all
python scripts/run_predefined_query_tests.py dry-run --technology NGINX --limit 5
```

`dry-run` uses the engine's `assess_execution_capability` + a no-network path, so
it reports readiness without connecting anywhere.

## 4. Docker test targets (profiles)

`docker-compose.predefined-queries.yml` brings up ONLY the technology targets,
grouped by weight so laptops are not overwhelmed:

| Profile | Services | Rough fit |
|---|---|---|
| `minimal` | nginx, postgres, redis, ubuntu | ~8 GB |
| `standard` | + mysql, apache, tomcat, mongodb | 16 GB comfortable |
| `extended` | + oracle, sqlserver | 16 GB+ / licensing |

```bash
docker compose -f docker-compose.predefined-queries.yml --profile minimal up -d
# run controls, then:
docker compose -f docker-compose.predefined-queries.yml --profile minimal down
```

Container names match `config/predefined_query_targets.local.yaml`, so the
docker-exec/TCP connectors resolve them directly. (The main `docker-compose.yml`
also provides these services behind its own profiles — use whichever fits.)

## 5. What the tests guarantee

- Catalog loads; **no duplicate control IDs**; every predefined control has a
  framework + technology; supplementary controls are allow-list gated with
  query + evidence_type + technology.
- All four target registries (`local/uat/prod/dr`) load and validate; every
  target has the required fields and a known technology.
- **localhost is allowed only in `local`** and is rejected for uat/prod/dr;
  remote registries contain no inline secrets.
- The predefined-queries compose has `minimal ⊆ standard ⊆ extended` profiles.
- The runner's inventory + `validate-targets` work offline.

## 6. Troubleshooting tests

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` (psycopg2/openpyxl/yaml) | install `requirements.txt` + `requirements-dev.txt` in the venv |
| Catalog total assertion changed | a catalog edit changed the count — update the count test intentionally and regenerate the inventory |
| Registry validation FAIL | run `python scripts/run_predefined_query_tests.py validate-targets <env>` to see the exact error |
| Docker target not found at runtime | bring up the matching profile of `docker-compose.predefined-queries.yml` |
