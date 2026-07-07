# ECS Asset Discovery & Technology Fingerprinting Guide

**Module:** Audit Intelligence — Module 2 (Milestone 1)
**Package:** `modules/audit_intelligence/`
**Status:** Engines + service + CLI + tests (no routes/UI yet — deferred to a later milestone).

---

## 1. Purpose

Automatically build a **unified asset inventory** from multiple sources, infer each
asset's **technology (and version)** with a **confidence score**, and cross-link
every asset to the **controls and frameworks** applicable to its technology (via the
[Technology Mapping](../developer-manual/TECHNOLOGY_MAPPING_GUIDE.md) engine). This produces the
coverage foundation later milestones (Evidence Orchestrator, Validation,
Dashboards) build on.

```
Sources -> normalize -> Asset -> fingerprint (technology/version/confidence) -> link controls/frameworks
```

Everything is **deterministic and offline** — no live network or Docker daemon is
required (and no credentials/secrets are ever stored on an asset record).

---

## 2. Architecture

```
modules/audit_intelligence/
  models.py                             # Asset, TechnologyFingerprint (frozen, to_dict())
  engines/asset_discovery.py            # source normalization -> unified Asset
  engines/technology_fingerprint.py     # deterministic technology/version/confidence inference
  services/asset_service.py             # inventory / technology-inventory / fingerprint report / coverage
```

### Unified `Asset` shape

`asset_id`, `hostname`, `environment`, `application`, `owner`, `technology`,
`version`, `operating_system`, `cloud`, `criticality`, `confidence_score`,
`source`, `fingerprint` (a `TechnologyFingerprint`), `applicable_control_ids`,
`applicable_frameworks`, `raw` (original non-secret source fields).

---

## 3. Discovery sources

| Source | Function | Live? | Notes |
|---|---|---|---|
| Manual import | `discover_from_manual(records)` | offline | list of dicts (e.g. a CSV/JSON import) |
| ServiceNow CMDB | `discover_from_servicenow(transport=…)` | needs transport | reuses the `ServiceNowCmdbClient` skeleton; **inject a transport** (mock in tests). Returns `[]` if not configured. |
| Docker demo | `discover_from_docker_compose(path=None)` | offline | parses `docker-compose.yml` **without** the Docker daemon |
| Enterprise GRC CMDB | `discover_from_enterprise_grc(role)` | offline | reuses the existing `build_cmdb_inventory` |
| Aggregate | `discover(**sources)` | mixed | runs the enabled sources, de-dupes by `asset_id` (first wins) |

> **Roadmap:** future cloud provider APIs (AWS/Azure/GCP) plug in as additional
> `discover_from_*` sources returning the same `Asset` shape.

---

## 4. Technology fingerprinting

`technology_fingerprint.fingerprint_asset(hints)` infers a technology from
whatever signals are available, in priority order:

1. **Explicit** `technology` hint (confidence ≈ 0.95)
2. **Container image** (e.g. `postgres:16.2`) (≈ 0.90) + version from the tag
3. **Host/service/container name** (e.g. `nginx-demo`) (≈ 0.60)
4. **Listening port** (e.g. `1433 → SQL Server`) (≈ 0.50)
5. **CMDB class / asset type** (coarse) (≈ 0.55)

Independent corroborating signals add a small boost (e.g. image **and** port agree).
Every inference records the **signals** that drove it, so results are auditable.
`matched_catalog_technology` flags whether the inferred technology exists in the
predefined-query catalog (i.e. whether controls can be linked).

Confidence bands (used in reports): `high ≥ 0.8`, `medium ≥ 0.5`, `low > 0`,
`none = 0` (Unknown).

**Recognized technologies** align with the catalog: PostgreSQL, YugabyteDB, Aurora
MySQL, Oracle, SQL Server, MongoDB, Redis, NGINX, Apache HTTPD, Tomcat, Kubernetes,
OpenShift, RHEL 8.x/9.x, Linux, Windows.

---

## 5. Service facade (`asset_service`)

| Function | Returns |
|---|---|
| `discover_assets(**sources)` | `list[Asset]` |
| `inventory(assets)` | serialized asset dicts |
| `technology_inventory(assets)` | per-technology roll-up (count, environments, avg confidence, applicable frameworks) |
| `fingerprint_report(assets)` | per-asset fingerprint detail + confidence banding |
| `coverage_summary(assets)` | identification rate, catalog coverage, applicable controls/frameworks, breakdowns by source/criticality/environment |

---

## 6. Usage

### Python

```python
from modules.audit_intelligence.services import asset_service as svc

assets = svc.discover_assets(
    manual_records=[{"asset_id": "web-1", "image": "nginx:1.25", "environment": "UAT"}],
    include_docker_compose=True,
)
svc.coverage_summary(assets)
svc.technology_inventory(assets)
```

ServiceNow (inject a transport; **never** a real call in tests):

```python
from modules.audit_intelligence.engines import asset_discovery as disco

def transport(method, url, headers, params):
    return {"result": [{"sys_id": "1", "name": "db-postgres-01",
                        "sys_class_name": "cmdb_ci_server", "used_for": "UAT"}]}

assets = disco.discover_from_servicenow(transport=transport)  # needs ECS_SERVICENOW_BASE_URL set
```

### CLI (read-only, offline)

```bash
python scripts/audit_intelligence_report.py --section assets --docker-compose
python scripts/audit_intelligence_report.py --section assets --enterprise-grc
python scripts/audit_intelligence_report.py --section assets --json
```

---

## 7. Tests

`tests/test_technology_fingerprint.py` — image/name/port/explicit inference,
version-from-tag, no false version from index suffixes, precedence, port-spec
parsing, unknown handling, audit signals.
`tests/test_asset_discovery.py` — each source (ServiceNow via **mock transport**,
manual, docker-compose temp-file + real repo file, enterprise-GRC), aggregation +
de-dup, and the service roll-ups/coverage.
`tests/test_audit_intelligence_report_cli.py` — the CLI harness.
All deterministic; no live Docker/network.

---

## 8. Assumptions & limitations

- **Versioning** is best-effort from image tags only (no live banner probing) — a
  deliberate trade-off for offline determinism. Bare integer suffixes in names
  (e.g. `ecs-redis-1`) are intentionally **not** treated as versions.
- **ServiceNow discovery** requires an injected/live transport and
  `ECS_SERVICENOW_BASE_URL`; the skeleton refuses real calls, so it is safe by
  default and returns `[]` when unconfigured.
- **No persistence** — discovery is computed on demand (persistence belongs to the
  Evidence Repository in a later milestone).
- No routes/UI yet (deferred); the service facade already returns UI-ready dicts.
