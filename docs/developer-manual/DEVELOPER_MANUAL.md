# ECS Developer Manual

The single entry point for developing ECS: run it locally, run tests, and extend
it (connectors, predefined queries, prompt tests, DB Agent, workbenches). Each
task links to its authoritative guide — this page is the map.

> **Reuse note.** The deep content already exists (engineering handbook,
> onboarding, setup). This manual unifies the "how do I…?" tasks in one place and
> links out; it does not duplicate.

---

## Run ECS locally
- Quickstart / demo mode: [`../00-start-here/DEMO_MODE_SETUP.md`](../00-start-here/DEMO_MODE_SETUP.md), [`../00-start-here/COMMON_COMMANDS.md`](../00-start-here/COMMON_COMMANDS.md)
- Full local setup: [`DEVELOPER_SETUP_GUIDE.md`](DEVELOPER_SETUP_GUIDE.md), [`LOCAL_DEVELOPMENT_GUIDE.md`](LOCAL_DEVELOPMENT_GUIDE.md)
- Prototype (no tokens/certs/vault): [`../operations/PROTOTYPE_DEMO_RUN_MODE.md`](../operations/PROTOTYPE_DEMO_RUN_MODE.md)

```bash
pip install -r requirements.txt
DEMO_MODE=true uvicorn app.main:app --port 8000   # http://127.0.0.1:8000/dashboard
```

## Run tests
- Full test map: [`../testing/TESTING_GUIDE.md`](../testing/TESTING_GUIDE.md)
- Smoke: [`../testing/E2E_SMOKE_TEST_GUIDE.md`](../testing/E2E_SMOKE_TEST_GUIDE.md)

```bash
python -m compileall -q app modules scripts tests config
PYTHONPATH=. pytest -q
```

## Add a connector
- Guide: [`../connectors/INTEGRATION_ADAPTERS_GUIDE.md`](../connectors/INTEGRATION_ADAPTERS_GUIDE.md) §7 (add an adapter)
- Reuse an existing platform client via the bridge (`_platform_bridge.py`) — see
  the GitHub/Jenkins/Azure DevOps adapters for the pattern.
- Wire: `ADAPTER_MODULES` (registry) → `_ADAPTER_TESTS` (workbench) →
  `_CONNECTOR_ROUTES` (scheduler); the executor picks it up automatically.

## Add predefined queries
- [`PREDEFINED_DATABASE_QUERY_MODULE.md`](PREDEFINED_DATABASE_QUERY_MODULE.md) (add queries/connectors/run)
- Catalog: [`PREDEFINED_QUERY_CATALOG.md`](PREDEFINED_QUERY_CATALOG.md)

## Add / run prompt tests
- [`PROMPT_TESTING_GUIDE.md`](PROMPT_TESTING_GUIDE.md) — Ollama/Gemini, prompt inventory, execution, replay, comparison, benchmarking, token metrics, grounding/hallucination.

## Run the DB Agent
- [`DATABASE_AGENT_GUIDE.md`](DATABASE_AGENT_GUIDE.md) (`python -m db_agent`)

## Use the workbenches
- Connector Test Workbench: [`TEST_WORKBENCH_GUIDE.md`](TEST_WORKBENCH_GUIDE.md)
- LLM Prompt Workbench: [`../workbenches/audit_llm_prompt_workbench_design.md`](../workbenches/audit_llm_prompt_workbench_design.md)

---

## Deeper references
- Engineering handbook (authoritative): [`ECS_ENGINEERING_HANDBOOK.md`](ECS_ENGINEERING_HANDBOOK.md)
- Onboarding: [`ECS_DEVELOPER_ONBOARDING_GUIDE.md`](ECS_DEVELOPER_ONBOARDING_GUIDE.md)
- API reference: [`ECS_API_REFERENCE.md`](ECS_API_REFERENCE.md)
- Architecture: [`../architecture/ARCHITECTURE_INDEX.md`](../architecture/ARCHITECTURE_INDEX.md)
- Module ownership: [`ECS_MODULE_OWNERSHIP.md`](ECS_MODULE_OWNERSHIP.md)
