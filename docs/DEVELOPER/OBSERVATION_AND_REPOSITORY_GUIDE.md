# ECS Observation, Evidence Repository & Packs Guide

**Module:** Audit Intelligence — Milestone 3
**Package:** `modules/audit_intelligence/`

Covers three engines: Observation Generation, the Evidence Repository (versioning
+ hash + timeline + search), and Evidence Packs (with JSON manifests).

---

## 1. Observation Generation (`engines/observation_generation.py`)

Converts failing/warning validations into audit **observations** —
deterministically, **no LLM**.

**Fields:** observation_id, technology, asset_id, control_id, frameworks, severity,
observation, impact, recommendation, evidence_reference, owner, status, timestamps,
history.

**Severity (deterministic):**
- `WARNING` → `Medium` (regulatory framework) else `Low`.
- `FAIL` → `Critical` (regulatory framework **and** assertion rule) / `High`
  (either) / `Medium` (neither).
- Regulatory frameworks: PCI DSS, RBI Cyber Security, DPSC, SOC2, ISO27001.

**Workflow:** `Draft → Submitted → Approved → Remediated → Closed`, with `Rejected`
(→ back to `Draft`). Transitions are validated; invalid moves raise
`InvalidTransition`. Every change is appended to `history`.

**API:** `generate_observation(result, …)`, `generate_from_results(results, …)`,
`transition(id, to_status)`, `list_observations(**filters)`, `get_observation(id)`,
`summary()`. Store is in-memory (`reset_observations()` for tests).

---

## 2. Evidence Repository (`engines/evidence_repository.py`)

Metadata store for collected evidence — **metadata + hash only, never secrets**.

- **Versioning:** each `store_evidence(...)` for the same `evidence_key`
  (`asset::control`) bumps the version (v1, v2, …).
- **Hash/checksum:** SHA-256 over the (non-secret) content excerpt + an 8-char
  checksum; identical content is detectable across versions.
- **Timeline:** chronological `stored` events per key (`timeline(key)`).
- **Search:** by technology / framework / asset / verdict / tag / free text;
  `latest_only` toggles latest-vs-all-versions.

**API:** `store_evidence(...)`, `store_from_run(run, results_by_control=…)`,
`get_versions(key)`, `get_latest(key)`, `all_latest()`, `timeline(key)`,
`search(...)`, `stats()`, `make_evidence_key(asset, control)`,
`reset_repository()`.

---

## 3. Evidence Packs (`engines/evidence_packs.py`)

Assemble audit-ready packs from the repository, each with a **JSON manifest**
containing per-item hashes/checksums and a **pack-level hash** (SHA-256 over the
sorted item hashes — deterministic and verifiable).

| Builder | Scope |
|---|---|
| `evidence_pack(keys)` | explicit evidence keys |
| `framework_pack(framework)` | all latest evidence for a framework |
| `asset_pack(asset_id)` | all latest evidence for an asset |
| `application_pack(app, asset_ids)` | evidence across an application's assets |
| `technology_pack(technology)` | all latest evidence for a technology |

`verify_manifest(manifest)` recomputes the pack hash from the item hashes and
compares (tamper detection). `manifest_json(manifest)` emits canonical sorted-key
JSON.

---

## 4. Service facade (`services/audit_repository_service.py`)

`list_observations` / `get_observation` / `transition_observation` /
`observation_summary`; `repository_search` / `evidence_versions` /
`evidence_timeline` / `repository_stats`; `build_pack(type, scope, asset_ids=…)` /
`verify_pack`. All return serialized dicts.

---

## 5. Usage

```python
from modules.audit_intelligence.engines import (
    observation_generation as obs, evidence_repository as repo, evidence_packs as packs,
)

# From validation results -> observations
observations = obs.generate_from_results(results, asset_id="web-1", owner="InfraOps")
obs.transition(observations[0].observation_id, "Submitted", user="alice")

# Persist evidence (versioned) + build a verifiable framework pack
repo.store_from_run(run, results_by_control={r.control_id: r for r in results})
pack = packs.framework_pack("PCI DSS")
assert packs.verify_manifest(pack)
```

---

## 6. Tests

`tests/test_observation_generation.py`, `tests/test_evidence_repository.py`,
`tests/test_evidence_packs.py` — severity derivation, workflow transitions,
versioning/hash, timeline, search, pack manifests + tamper detection. Offline.

---

## 7. Assumptions & limitations

- **In-memory stores** (observations + repository) — the public API is DB-ready;
  swapping in durable persistence later needs no caller changes.
- **Application packs** take explicit `asset_ids` (applications aren't yet persisted
  with first-class asset linkage). Documented assumption.
- Observation text is templated deterministically from the validation result
  (no LLM); wording can be enriched later without interface changes.
