# ECS developer Makefile — convenience wrappers around the commands the repo
# already uses (see docs/00-start-here/COMMON_COMMANDS.md and .github/workflows/ci.yml).
# Everything runs offline in DEMO_MODE by default (no external DB/IdP/LLM required).

PY ?= python3
VENV ?= .venv
PYBIN := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
export PYTHONPATH := .
export DEMO_MODE ?= true
export ECS_AUTH_ENABLED ?= false
export ECS_VALIDATE_CONFIG ?= off

# Offline-safe targeted suites (mirror CI).
CI_TESTS := \
	tests/test_connector_execution_ingestion.py \
	tests/test_batch2_rest_ui.py \
	tests/test_rag_answer_validation.py \
	tests/test_audit_llm_workbench.py \
	tests/test_uat_asset_scheduler.py \
	tests/test_connector_test_workbench.py \
	tests/test_evidence_repository.py \
	tests/test_production_hardening.py \
	tests/test_enterprise_gap_close.py \
	tests/test_scheduler_execution.py \
	tests/test_audit_llm_evaluation.py \
	tests/test_cloud_security_connectors.py \
	tests/test_usecase_batch1_evidence_workflows.py \
	tests/test_evidence_reuse_lifecycle.py

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: venv
venv: ## Create the virtualenv if missing
	@test -d $(VENV) || $(PY) -m venv $(VENV)

.PHONY: install
install: venv ## Install runtime + dev dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@test -f requirements-dev.txt && $(PIP) install -r requirements-dev.txt || true

.PHONY: install-locked
install-locked: venv ## Reproducible install from requirements.lock (pinned)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.lock

.PHONY: lock
lock: ## Regenerate requirements.lock from the current (known-good) venv
	$(PYBIN) scripts/gen_requirements_lock.py > requirements.lock
	@echo "requirements.lock regenerated"

.PHONY: run
run: ## Run ECS locally in demo mode (http://127.0.0.1:8000)
	$(PYBIN) -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

.PHONY: compile
compile: ## Byte-compile app/modules/scripts/tests/config (syntax check)
	$(PYBIN) -m compileall -q app modules scripts tests config

.PHONY: test
test: ## Run the offline-safe targeted test suites (as CI does)
	$(PYBIN) -m pytest -q -p no:cacheprovider $(CI_TESTS)

.PHONY: test-all
test-all: ## Run the full test suite (may need services/flags)
	$(PYBIN) -m pytest -q

.PHONY: ci
ci: compile test ## Run the same checks as GitHub Actions CI

.PHONY: smoke
smoke: ## Run the demo smoke script
	$(PYBIN) scripts/run_ecs_demo_smoke.py

.PHONY: benchmark
benchmark: ## Dry-run the local LLM benchmark (16 GB profile)
	$(PYBIN) scripts/run_audit_llm_benchmark.py --profile local_16gb_safe --mode dry_run

.PHONY: scheduler-dry-run
scheduler-dry-run: ## Dry-run the UAT asset scheduler
	$(PYBIN) scripts/run_uat_asset_scheduler.py --dry-run

.PHONY: lint
lint: ## Lint with ruff if available (non-fatal otherwise)
	@$(PYBIN) -m ruff --version >/dev/null 2>&1 && $(PYBIN) -m ruff check app modules scripts tests || \
		echo "ruff not installed; skipping (pip install ruff to enable)"

.PHONY: format
format: ## Format with ruff if available (non-fatal otherwise)
	@$(PYBIN) -m ruff --version >/dev/null 2>&1 && $(PYBIN) -m ruff format app modules scripts tests || \
		echo "ruff not installed; skipping (pip install ruff to enable)"

.PHONY: clean
clean: ## Remove Python caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -prune -exec rm -rf {} + 2>/dev/null || true
