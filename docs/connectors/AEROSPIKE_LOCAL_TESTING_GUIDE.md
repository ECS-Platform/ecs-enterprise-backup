# Aerospike — Local Testing & Predefined Query Guide

How to run, classify, and collect evidence from **Aerospike** in ECS. Aerospike is
integrated using the **existing** predefined-query engine, technology catalog,
fingerprint engine, and asset scheduler — no parallel engine was added.

> Cross-refs: [PREDEFINED_DATABASE_QUERY_MODULE.md](../developer-manual/PREDEFINED_DATABASE_QUERY_MODULE.md)
> (query engine), [README_DEVELOPER.md](../developer-manual/README_DEVELOPER.md) (env/Docker),
> [UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](../scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md)
> (asset routing), [ECS_DEVELOPER_ONBOARDING_GUIDE.md](../developer-manual/ECS_DEVELOPER_ONBOARDING_GUIDE.md).

**Safety:** no secrets, no real IPs. Host port **3000 is reserved for Gitea**, so
Aerospike uses **13000** locally.

---

## 1. Why 13000 (not 3000)

Aerospike's client service listens on container port **3000**, but the local ECS
stack already maps host **3000 → Gitea**. To avoid a port conflict, ECS maps
Aerospike to the **13000 range** on the host:

```
container 3000 (service)   → host ${AEROSPIKE_HOST_PORT:-13000}
container 3001 (fabric)    → host ${AEROSPIKE_FABRIC_PORT:-13001}
container 3002 (heartbeat) → host ${AEROSPIKE_HEARTBEAT_PORT:-13002}
```

---

## 2. Run Aerospike locally

### Option A — standalone container (matches the pulled image)
```bash
docker pull aerospike/aerospike-server:latest

docker run -d \
  --name ecs-aerospike \
  -p 13000:3000 \
  -p 13001:3001 \
  -p 13002:3002 \
  aerospike/aerospike-server:latest
```

### Option B — via ECS docker-compose (opt-in profile)
```bash
docker compose --profile aerospike up -d aerospike
```
The compose service is `aerospike` (container `ecs-aerospike`) under the
`aerospike` and `demo` profiles. It is **not** started by default.

### Environment
```bash
export AEROSPIKE_HOST=localhost
export AEROSPIKE_PORT=13000
export AEROSPIKE_NAMESPACE=test
```
Placeholders live in `.env.example` (`AEROSPIKE_HOST/PORT/NAMESPACE/USER/PASSWORD/
TLS_ENABLED` + host-port mappings). The community demo has security **off**, so
`AEROSPIKE_USER`/`AEROSPIKE_PASSWORD` are blank; provide a **read-only** account
for real UAT (via env / secret store, never committed).

---

## 3. Aerospike predefined queries

Twenty read-only checks (`ASX-001` … `ASX-020`) are defined in the **supplementary
query catalog** (`modules/operations/engines/supplementary_query_catalog.py`) —
the same additive mechanism used by the other technologies. They run the
`asinfo` / `asadm` CLI tools.

| ID | Check | Command (abridged) |
|----|-------|--------------------|
| ASX-001 | Server version | `asinfo -v "build"` |
| ASX-002 | Cluster status | `asinfo -v "status"` |
| ASX-003 | Namespace list | `asinfo -v "namespaces"` |
| ASX-004 | Namespace config | `asinfo -v "get-config:context=namespace;id=${AEROSPIKE_NAMESPACE:-test}"` |
| ASX-005 | Security config | `asinfo -v "get-config:context=security"` |
| ASX-006 | User/role list | `asadm -e "show users"` |
| ASX-007 | TLS config | `asinfo -v "get-config:context=network"` |
| ASX-008 | Service ports | `asinfo -v "get-config:context=service"` |
| ASX-009 | Storage engine config | `asinfo -v "get-config:context=namespace;id=…"` |
| ASX-010 | Backup posture | `asadm -e "show config"` |
| ASX-011 | XDR config | `asinfo -v "get-config:context=xdr"` |
| ASX-012 | Audit logging | `asinfo -v "get-config:context=security"` |
| ASX-013 | Memory usage | `asadm -e "show stat"` |
| ASX-014 | Index usage | `asinfo -v "statistics"` |
| ASX-015 | Cluster node count | `asinfo -v "statistics"` |
| ASX-016 | Replication factor | `asinfo -v "get-config:context=namespace;id=…"` |
| ASX-017 | Strong consistency | `asinfo -v "get-config:context=namespace;id=…"` |
| ASX-018 | Expiration/TTL | `asinfo -v "get-config:context=namespace;id=…"` |
| ASX-019 | Secondary index list | `asinfo -v "sindex"` |
| ASX-020 | Latency / slow query | `asinfo -v "statistics"` |

The `${AEROSPIKE_NAMESPACE:-test}` placeholder is resolved from `AEROSPIKE_NAMESPACE`
at execution time.

---

## 4. Run a query (existing run-query flow)

Aerospike is dispatched by the existing `predefined_queries_engine.run_predefined_query()`.
Selecting **Aerospike** in the Predefined Queries screen (`/mvp/predefined-queries`)
filters to the `ASX-*` controls; **Run Query** routes them to the Aerospike path.

- **Demo mode** (`DEMO_MODE=true`): returns **deterministic synthetic output**
  (prefixed `[DEMO]`) — no container, no network, no hang. This is the offline-safe
  default consistent with every other ECS technology.
- **Live / UAT** (`DEMO_MODE` unset, target configured): runs
  `docker exec ecs-aerospike asinfo|asadm …` against the node
  (`AEROSPIKE_HOST/PORT/NAMESPACE`). Never calls a target unless configured.

Programmatic example:
```python
from modules.operations.engines import predefined_queries_engine as e
result = e.run_predefined_query("ASX-001", user="tester")   # -> {"ok": True, "output": "[DEMO] build\t7.1.0.0", ...}
```

CLI (offline end-to-end smoke, includes technology coverage):
```bash
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py
```

---

## 5. Technology dropdown — how it works & troubleshooting

**The Technology dropdown is data-driven, not hardcoded.** It is built by
`predefined_queries_engine.get_technology_filter_options()`, which returns the
**distinct `technology` values across all loaded controls**
(`get_all_controls()`), rendered by `mvp_predefined_queries.html` via
`module_view.technology_options`.

Consequently, **a technology appears in the dropdown if and only if at least one
loaded control has that technology.** Aerospike now appears because the 20 `ASX-*`
controls declare `technology = "Aerospike"`.

### "A technology is missing from the dropdown" — checklist
1. **Are there controls for it?** `get_all_controls()` must contain ≥1 control with
   that `technology`. If not, add them to the supplementary catalog (as Aerospike
   was) or the Excel library.
2. **Did the catalog load?** If the Excel workbook is missing/unreadable, only the
   supplementary (code-defined) controls load. Check
   `predefined_queries_engine.validate_startup()` / `load_predefined_queries()`.
3. **Is the technology detected?** For Excel rows without an explicit technology,
   `detect_technology()` infers it from the query text via `TECHNOLOGY_RULES`; if
   nothing matches it becomes `Unknown`. Supplementary entries state `technology`
   explicitly (preferred).
4. **Peers not seeing it after pulling code?** The dropdown is computed at request
   time from the loaded controls — no DB, seed, or static-JS dependency. After a
   `git pull`, restart the app (the catalog is loaded once and cached in-process);
   the new technology then appears for everyone. No per-user/config step is needed.

---

## 6. Fingerprinting & asset scheduler

The fingerprint engine (`technology_fingerprint.py`) classifies Aerospike from:
- `technology_hint: aerospike` (explicit),
- image `aerospike/aerospike-server`,
- service/container name containing `aerospike` (e.g. `ecs-aerospike`),
- ports **3000** (default) or **13000** (host-mapped).

The UAT asset scheduler
([design](../scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md)) then classifies an Aerospike
asset as a **baseline_collector** (scope `technology:Aerospike`, 20 controls),
since Aerospike is a predefined-query technology (not an enterprise connector).

```bash
# Add an Aerospike asset to config/uat_assets.local.yaml, then:
python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --dry-run
```

---

## 7. Tests

`tests/test_aerospike_support.py` (offline, no container) covers the compose
service, port defaults (13000, never host 3000), config placeholders, catalog +
dropdown, the 20 queries, run-query routing (demo output + namespace resolution),
fingerprinting, asset-scheduler classification, and secret/IP safety.

```bash
PYTHONPATH=. pytest tests/test_aerospike_support.py -q
```

---

## 8. Known limitations

- Live execution uses `docker exec ecs-aerospike …`; a remote/UAT Aerospike node
  needs the tools reachable (or an SSH/remote mode — a documented future extension,
  like the other shell connectors).
- Demo output is synthetic and fixed; it demonstrates the flow, not real cluster
  state.
- Security-off community demo returns empty user/role lists (expected); real UAT
  should enable security and use a read-only account.
