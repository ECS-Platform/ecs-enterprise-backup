#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"

echo "Testing ECS Evidence Reuse APIs at: $BASE_URL"
echo

check_get() {
  local path="$1"
  echo "GET $path"
  curl -sS -f "$BASE_URL$path" | python3 -m json.tool >/dev/null
  echo "OK"
  echo
}

check_post() {
  local path="$1"
  echo "POST $path"
  curl -sS -f -X POST "$BASE_URL$path" \
    -H "Accept: application/json" \
    | python3 -m json.tool >/dev/null
  echo "OK"
  echo
}

check_get "/api/evidence-reuse/records"
check_get "/api/evidence-reuse/readiness"
check_get "/api/evidence-reuse/observations"

check_post "/api/evidence-reuse/analyze"
check_post "/api/evidence-reuse/validate-completeness"
check_post "/api/evidence-reuse/generate-observations"
check_post "/api/evidence-reuse/check-closure"

echo "All Evidence Reuse API smoke tests passed."
