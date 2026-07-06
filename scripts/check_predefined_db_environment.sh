#!/usr/bin/env bash
# Convenience wrapper for the ECS predefined-database environment diagnostic.
# Works on macOS/Linux and Windows Git Bash. Safe and simple: it only sets
# PYTHONPATH, activates a local virtualenv if present, and runs the Python
# diagnostic. All arguments are passed through (e.g. --json, --skip-mysql).
#
#   scripts/check_predefined_db_environment.sh
#   scripts/check_predefined_db_environment.sh --json --skip-mysql
set -euo pipefail

# Resolve repo root as the parent of this script's directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

export PYTHONPATH="${REPO_ROOT}"

# Activate a virtualenv if one exists (Windows Git Bash uses Scripts/, POSIX uses bin/).
if [ -f ".venv/Scripts/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/Scripts/activate"
elif [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

# Prefer python, fall back to python3.
if command -v python >/dev/null 2>&1; then
  PY=python
else
  PY=python3
fi

exec "${PY}" scripts/check_predefined_db_environment.py "$@"
