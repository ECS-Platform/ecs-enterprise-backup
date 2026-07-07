# ECS Technology → Control → Framework Mapping Guide

**Module:** Audit Intelligence — Module 1 (Milestone 1)
**Package:** `modules/audit_intelligence/`
**Status:** Engine + service + CLI + tests (no routes/UI yet — deferred to a later milestone).

---

## 1. Purpose

The mapping engine answers audit-readiness questions by connecting the dots that
already exist in the predefined-query platform:

```
Technology  ->  Predefined Queries (Controls)  ->  Frameworks  ->  Evidence  ->  Audit Readiness
```

Example (NGINX):

```
NGINX
  -> NGX-001, NGX-002, ... , MW-001            (controls / predefined queries)
  -> TLS / config / logging controls
  -> RBI Cyber Security, PCI DSS, ISO27001, DPSC, Middleware Baselining   (frameworks)
  -> Evidence  ->  Audit Pass/Fail
```

It is a **read-only projection** over the existing catalog. It defines **no new
catalog** and **mutates nothing** — it aggregates the ~187 controls already loaded
by `predefined_queries_engine`.

---

## 2. Architecture

```
modules/audit_intelligence/
  models.py                          # ControlRef, TechnologyRef, FrameworkRef, MappingRow (frozen, to_dict())
  engines/technology_control_mapping.py   # derivation logic (this module)
  services/mapping_service.py        # serialization facade (dicts for future API/UI)
```

Data source: `modules.operations.engines.predefined_queries_engine.get_all_controls()`.
Each catalog control already carries `control_id`, `control_name`, `technology`,
`frameworks` (list), `category`, `description`, `query`, `predefined`, `executable`.
The engine normalizes these into `ControlRef` and aggregates them by technology and
by framework.

**Determinism:** all functions are pure and offline; the projection is cached
(`functools.lru_cache`) and can be cleared with `reset_cache()` after a forced
catalog reload.

---

## 3. Engine API (`technology_control_mapping`)

| Function | Returns | Notes |
|---|---|---|
| `all_controls()` | `list[ControlRef]` | normalized copy of every catalog control |
| `get_control(id)` | `ControlRef \| None` | single control |
| `controls_for_technology(tech)` | `list[ControlRef]` | case-insensitive |
| `controls_for_framework(fw)` | `list[ControlRef]` | case-insensitive |
| `list_technologies()` | `list[TechnologyRef]` | with control/framework counts |
| `get_technology(tech)` / `technology_names()` | `TechnologyRef` / `list[str]` | |
| `frameworks_for_technology(tech)` | `list[str]` | |
| `list_frameworks()` | `list[FrameworkRef]` | with control/technology counts |
| `get_framework(fw)` / `framework_names()` | `FrameworkRef` / `list[str]` | |
| `technologies_for_framework(fw)` | `list[str]` | |
| `frameworks_for_control(id)` / `technology_for_control(id)` | `list[str]` / `str \| None` | |
| `build_mapping_graph()` | `dict` | Technology → Controls → Frameworks + stats |
| `mapping_rows()` | `list[MappingRow]` | one flat row per control |
| `search_mappings(query, technology, framework)` | `list[MappingRow]` | filter |
| `mapping_stats()` | `dict` | coverage summary |
| `reset_cache()` | `None` | clear the memoized projection |

### Service facade (`mapping_service`)

Returns plain dicts/lists (via each model's `to_dict()`), a stable contract for a
future REST API / UI: `technologies()`, `frameworks()`, `controls()`,
`technology_detail(t)`, `framework_detail(f)`, `control_detail(id)`, `graph()`,
`search(...)`, `stats()`, `filter_options()`.

---

## 4. Usage

### Python

```python
from modules.audit_intelligence.engines import technology_control_mapping as mapping

mapping.mapping_stats()
# {'technologies': 20, 'controls': 167, 'frameworks': 16, 'executable_controls': 127, ...}

[c.control_id for c in mapping.controls_for_technology("NGINX")]
# ['MW-001', 'NGX-001', 'NGX-002', ...]

mapping.frameworks_for_technology("NGINX")
# ['DPSC', 'ISO27001', 'Middleware Baselining', 'PCI DSS', 'RBI Cyber Security']

mapping.search_mappings(technology="NGINX", framework="PCI DSS")
```

### CLI (read-only, offline)

```bash
python scripts/audit_intelligence_report.py --section mapping
python scripts/audit_intelligence_report.py --section mapping --technology NGINX
python scripts/audit_intelligence_report.py --section mapping --framework "PCI DSS"
python scripts/audit_intelligence_report.py --section mapping --json
```

---

## 5. Extending

- **New technology / control / framework:** add it in the **predefined-query
  catalog** (Excel workbook or `supplementary_query_catalog.py`). The mapping
  engine picks it up automatically — do **not** add a parallel catalog here.
- **New derived view:** add a pure function to `technology_control_mapping.py`
  and expose a serialized wrapper in `mapping_service.py`.

---

## 6. Tests

`tests/test_technology_control_mapping.py` — projection integrity, unique ids,
technology/framework counts, the NGINX example chain, roundtrips, graph shape,
search filters, and service serialization. Deterministic; no live Docker/DB.

---

## 7. Assumptions & limitations

- **Frameworks are derived from the catalog's `frameworks` field**, not from
  `modules/frameworks/framework_catalog.py`. This keeps the mapping strictly tied
  to what each predefined query actually evidences. (A future milestone can
  reconcile the two framework vocabularies if required.)
- Read-only and stateless — no persistence (that belongs to the Evidence
  Repository in a later milestone).
- No routes/UI yet (deferred); the service facade already returns UI-ready dicts.
