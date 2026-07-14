#!/usr/bin/env bash
# Idempotent ECS demo startup + technology health validation.
#
#   ./scripts/start_ecs_demo.sh --core
#   ./scripts/start_ecs_demo.sh --all
#   ./scripts/start_ecs_demo.sh --all --skip-heavy
#   ./scripts/start_ecs_demo.sh --technology SonarQube
#   ./scripts/start_ecs_demo.sh --status-only
#   ./scripts/start_ecs_demo.sh --help
#
# After a Mac restart Docker may leave optional targets stopped; this script
# starts existing compose services (with their declared profiles), waits for
# real readiness, validates connector runtime config, and prints a status table.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

export PYTHONPATH="${REPO_ROOT}"

if [ -f ".venv/Scripts/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/Scripts/activate"
elif [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

if command -v python >/dev/null 2>&1; then
  PY=python
else
  PY=python3
fi

exec "${PY}" scripts/ecs_demo_startup.py "$@"
