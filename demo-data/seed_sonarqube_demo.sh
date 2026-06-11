#!/usr/bin/env bash
# Repeatable SonarQube demo seeder for ECS.
# Creates/updates the "ecs-demo-app" project by running a SonarScanner analysis
# of demo-data/sonar-demo against the running sonarqube-demo container, so ECS
# can collect evidence (quality gate + security hotspots).
#
# Usage:
#   ./demo-data/seed_sonarqube_demo.sh
# Env overrides:
#   SONAR_HOST   (host-side URL, default http://localhost:9000)
#   SONAR_ADMIN_USER / SONAR_ADMIN_PASS (default admin / a123)
#   PROJECT_KEY / PROJECT_NAME
set -euo pipefail

SONAR_HOST="${SONAR_HOST:-http://localhost:9000}"
SONAR_IN_NET="${SONAR_IN_NET:-http://sonarqube-demo:9000}"
SONAR_ADMIN_USER="${SONAR_ADMIN_USER:-admin}"
SONAR_ADMIN_PASS="${SONAR_ADMIN_PASS:-a123}"
# NOTE: PROJECT_NAME must match the Gitea repo name and Jenkins job name so ECS
# correlates evidence into one Commit -> Build -> Sonar chain (grouped by application).
PROJECT_KEY="${PROJECT_KEY:-ecs-demo-app}"
PROJECT_NAME="${PROJECT_NAME:-ecs-demo-app}"
SCAN_DIR="$(cd "$(dirname "$0")/sonar-demo" && pwd)"

echo "==> SonarQube: $SONAR_HOST  project: $PROJECT_KEY"

# 1. Detect the compose network so the scanner can reach sonarqube-demo by name.
NET="$(docker network ls --format '{{.Name}}' | grep -E 'ecs.*default|default.*ecs' | head -1 || true)"
NET="${NET:-ecs_default}"
echo "==> Using docker network: $NET"

# 2. Create the project (ignore error if it already exists).
curl -s -u "$SONAR_ADMIN_USER:$SONAR_ADMIN_PASS" -X POST \
  "$SONAR_HOST/api/projects/create?project=$PROJECT_KEY&name=$(python3 -c "import urllib.parse,os;print(urllib.parse.quote(os.environ['PROJECT_NAME']))")" \
  >/dev/null || true

# 3. Generate a fresh analysis token (revoke old one first for idempotency).
curl -s -u "$SONAR_ADMIN_USER:$SONAR_ADMIN_PASS" -X POST \
  "$SONAR_HOST/api/user_tokens/revoke?name=ecs-demo-scan" >/dev/null || true
TOKEN="$(curl -s -u "$SONAR_ADMIN_USER:$SONAR_ADMIN_PASS" -X POST \
  "$SONAR_HOST/api/user_tokens/generate?name=ecs-demo-scan" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')"
echo "==> Analysis token generated"

# 4. Run the scan on the compose network.
docker run --rm --network "$NET" \
  -v "$SCAN_DIR:/usr/src" \
  sonarsource/sonar-scanner-cli \
  -Dsonar.host.url="$SONAR_IN_NET" \
  -Dsonar.token="$TOKEN" \
  -Dsonar.projectKey="$PROJECT_KEY" \
  -Dsonar.projectName="$PROJECT_NAME"

echo "==> Scan submitted; waiting for background analysis to finish..."
for i in $(seq 1 30); do
  STATUS="$(curl -s -u "$SONAR_ADMIN_USER:$SONAR_ADMIN_PASS" \
    "$SONAR_HOST/api/qualitygates/project_status?projectKey=$PROJECT_KEY" \
    | python3 -c 'import sys,json
try:
  print(json.load(sys.stdin)["projectStatus"]["status"])
except Exception:
  print("PENDING")' 2>/dev/null || echo PENDING)"
  if [ "$STATUS" != "PENDING" ] && [ "$STATUS" != "NONE" ]; then
    echo "==> Quality gate status: $STATUS"
    break
  fi
  sleep 3
done

echo "==> Done. Project '$PROJECT_KEY' is ready for ECS sync."
