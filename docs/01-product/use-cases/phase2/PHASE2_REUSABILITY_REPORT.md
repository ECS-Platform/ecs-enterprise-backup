# Phase-2 Encryption Control Reusability Report

## Goal

Extend the Phase-2 simulation so **Encryption at Rest** and **Encryption in Transit**
run across configured applications using reusable technology adapters — without
application-specific collectors or scheduler/UI/RAG changes.

## Applications (CONFIGURATION)

| Application | Technologies used for encryption controls |
|-------------|---------------------------------------------|
| Net Banking | Aurora MySQL (at rest), NGINX (in transit), Aurora DB-TLS |
| Mobile Banking | PostgreSQL, MySQL, YugabyteDB, Aerospike (at rest + DB-TLS); NGINX (web TLS) |
| Payments | PostgreSQL (at rest + DB-TLS), Tomcat (API TLS) |
| Demo Card Portal (dummy) | PostgreSQL + NGINX — **config-only onboarding** |

## Controls

1. Encryption at Rest → Phase-1 `CommonControls/encryption-at-rest`
2. Encryption in Transit → Phase-1 `CommonControls/encryption-in-transit`

## Classification

| Item | Class | Notes |
|------|-------|-------|
| `config/phase2_application_portfolio.yaml` | **CONFIGURATION** | Apps, assets, tech stacks, control prefs, multi-tech flag |
| `data/phase2-reusability/fixtures/<tech>/*.json` | **CONFIGURATION** | Deterministic mock evidence |
| `phase2_tech_adapters.py` | **REUSABLE_ADAPTER** | Technology-keyed loaders + canonical field normalization |
| `phase2_reusability.py` | **CORE_ECS_CHANGE** | Config-driven fan-out over existing collector |
| `common_controls_collector` `application_context` | **CORE_ECS_CHANGE** | Optional overlay; Phase-1 unchanged when absent |
| Scheduler / UI / RAG | **None** | Untouched |

## Adapters reused vs added

| Technology | At Rest | In Transit | Status |
|------------|---------|------------|--------|
| aurora_mysql | yes | yes (DB-TLS) | reused/extended |
| mysql | yes | yes (DB-TLS) | **added** |
| postgresql | yes | yes (DB-TLS) | reused/extended |
| yugabyte | yes | yes (DB-TLS) | reused/extended |
| aerospike | yes | yes (DB-TLS) | **added** |
| nginx | — | yes (web TLS) | reused |
| tomcat | — | yes (API TLS) | reused |

## Design rules honored

- Application/asset/technology from YAML only
- Same CommonControls manifests + `validate_evidence` / custody / `register_upload`
- No NetBanking/MobileBanking/Payments collectors
- Multi-tech fan-out via `collect_all_matching_technologies`
- Dummy app onboarded by YAML alone

## Tests

`tests/test_phase2_reusability.py` — NetBanking, Mobile multi-tech, Payments, adapter reuse, config-only dummy app, tagging, hashing/storage, Phase-1 scheduler untouched.

## Remaining gaps

- Live connector execution for encryption controls is still fixture-backed (no live Aurora/Aerospike probes in this simulation).
- Secure Configuration / Least Privilege remain in the earlier Phase-2 matrix design but are out of scope for this encryption-focused extension.
- RAG/UI not wired to Phase-2 simulation entrypoint (by design).
