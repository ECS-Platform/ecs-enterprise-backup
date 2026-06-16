#!/bin/bash
# Capture ECS product-manual screenshots with headless Chrome.
# Usage: ./demo-data/capture_product_manual.sh
# Requires ECS running in demo mode on http://127.0.0.1:8000
# (DEMO_MODE=true ECS_AUTH_ENABLED=false uvicorn app.main:app)
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT="docs/product_manual/screenshots"
BASE="http://127.0.0.1:8000"
mkdir -p "$OUT"
pkill -9 -f "headless=new" 2>/dev/null
rm -rf /tmp/cr-pm-* 2>/dev/null

shoot () {
  local name="$1" url="$2"
  rm -rf "/tmp/cr-pm-$name"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --no-sandbox \
    --no-first-run --no-default-browser-check --virtual-time-budget=9000 \
    --force-device-scale-factor=1 --window-size=1600,2200 \
    --user-data-dir="/tmp/cr-pm-$name" \
    --screenshot="$OUT/$name.png" "$BASE$url" >/dev/null 2>&1 &
  local pid=$!
  local waited=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 1; waited=$((waited+1))
    if [ -s "$OUT/$name.png" ] && [ "$waited" -ge 4 ]; then kill -9 "$pid" 2>/dev/null; break; fi
    if [ "$waited" -ge 18 ]; then kill -9 "$pid" 2>/dev/null; break; fi
  done
  wait "$pid" 2>/dev/null
  echo "$name.png -> $(stat -f%z "$OUT/$name.png" 2>/dev/null || echo MISSING) bytes"
}

# name::url specs. Roles chosen to match each screen's primary persona.
SPECS=(
  "01-login::/"
  "02-dashboard-owner::/dashboard?role=owner&user=AppOwner"
  "03-dashboard-auditor::/dashboard?role=auditor&user=Auditor"
  "04-dashboard-cio::/dashboard/cio?role=cio&user=CIO"
  "05-dashboard-vertical-head::/dashboard/vertical-head?role=vertical_head&user=VerticalHead"
  "06-dashboard-compliance-head::/dashboard/compliance-head?role=compliance_head&user=ComplianceOfficer"
  "07-dashboard-functional-head::/dashboard/functional-head?role=functional_head&user=FunctionalHead"
  "08-roi-center::/mvp/roi?role=cio&user=CIO"
  "09-demo-overview::/mvp/demo-overview?role=cio&user=CIO"
  "10-enterprise::/mvp/enterprise?role=cio&user=CIO"
  "11-pan-india::/mvp/pan-india?role=cio&user=CIO"
  "12-reports::/mvp/reports?role=auditor&user=Auditor"
  "13-trends::/mvp/trends?role=cio&user=CIO"
  "14-framework-pci-dss::/framework/PCI DSS?role=auditor&user=Auditor"
  "15-framework-loader::/mvp/framework-loader?role=compliance_head&user=ComplianceOfficer"
  "16-framework-admin::/mvp/framework-admin?role=framework_owner&user=FrameworkOwner"
  "17-scheduler::/mvp/scheduler?role=operations_owner&user=OpsOwner"
  "18-predefined-queries::/mvp/predefined-queries?role=operations_owner&user=OpsOwner"
  "19-integration-health::/mvp/integration-health?role=admin&user=Admin"
  "20-evidence-explorer::/mvp/evidence-explorer?role=admin&user=Admin"
  "21-ai-ops-assistant::/mvp/ai-ops-assistant?role=operations_owner&user=OpsOwner"
  "22-bulk-upload::/mvp/upload?role=owner&user=AppOwner"
  "23-integrations::/mvp/integrations?role=operations_owner&user=OpsOwner"
  "24-onboarding::/mvp/onboarding?role=operations_owner&user=OpsOwner"
  "25-audit-prep::/mvp/audit-prep?role=auditor&user=Auditor"
  "26-evidence-health::/mvp/evidence-health?role=owner&user=AppOwner"
  "27-evidence-reuse::/mvp/reuse?role=compliance_head&user=ComplianceOfficer"
  "28-lifecycle::/mvp/lifecycle?role=compliance_head&user=ComplianceOfficer"
  "29-completeness::/mvp/completeness?role=compliance_head&user=ComplianceOfficer"
  "30-comparison::/mvp/comparison?role=vertical_head&user=VerticalHead"
  "31-search::/mvp/search?role=auditor&user=Auditor"
  "32-evidence-approval::/mvp/evidence-approval?role=auditor&user=Auditor"
  "33-platform-scorecard::/mvp/platform/scorecard?role=cio&user=CIO"
  "34-platform-executive-summary::/mvp/platform/executive-summary?role=cio&user=CIO"
  "35-platform-audit-readiness::/mvp/platform/audit-readiness?role=auditor&user=Auditor"
  "36-platform-onboarding::/mvp/platform/onboarding?role=admin&user=Admin"
  "37-platform-inventory::/mvp/platform/inventory?role=admin&user=Admin"
  "38-platform-control-coverage::/mvp/platform/control-coverage?role=compliance_head&user=ComplianceOfficer"
  "39-platform-framework-coverage::/mvp/platform/framework-coverage?role=compliance_head&user=ComplianceOfficer"
  "40-platform-evidence-reuse::/mvp/platform/evidence-reuse?role=compliance_head&user=ComplianceOfficer"
  "41-platform-evidence-lifecycle::/mvp/platform/evidence-lifecycle?role=admin&user=Admin"
  "42-platform-scheduler::/mvp/platform/scheduler?role=admin&user=Admin"
  "43-ai-assistant::/mvp/ai-assistant?role=auditor&user=Auditor"
  "44-risk-register::/mvp/risk-register?role=governance_lead&user=GovLead"
  "45-exceptions::/mvp/exceptions?role=compliance_head&user=ComplianceOfficer"
  "46-exception-governance::/mvp/exception-governance?role=compliance_head&user=ComplianceOfficer"
  "47-cmdb::/mvp/cmdb?role=admin&user=Admin"
  "48-regulatory::/mvp/regulatory?role=compliance_head&user=ComplianceOfficer"
  "49-heatmaps::/mvp/heatmaps?role=cio&user=CIO"
  "50-integrations-hub::/mvp/integrations-hub?role=admin&user=Admin"
  "51-correlation::/mvp/correlation?role=admin&user=Admin"
  "52-governance-analytics::/mvp/governance-analytics?role=cio&user=CIO"
  "53-ai-sdlc-home::/mvp/ai-sdlc?role=ai_sdlc_owner&user=SDLCOwner"
  "54-ai-sdlc-control-tower::/mvp/ai-sdlc/control-tower?role=ai_sdlc_owner&user=SDLCOwner"
  "55-ai-sdlc-onboarding::/mvp/ai-sdlc/onboarding?role=ai_sdlc_owner&user=SDLCOwner"
  "56-ai-sdlc-requirements::/mvp/ai-sdlc/requirements?role=ai_sdlc_owner&user=SDLCOwner"
  "57-ai-sdlc-design::/mvp/ai-sdlc/design?role=ai_sdlc_owner&user=SDLCOwner"
  "58-ai-sdlc-development::/mvp/ai-sdlc/development?role=ai_sdlc_owner&user=SDLCOwner"
  "59-ai-sdlc-testing::/mvp/ai-sdlc/testing?role=ai_sdlc_owner&user=SDLCOwner"
  "60-ai-sdlc-golive::/mvp/ai-sdlc/golive?role=ai_sdlc_owner&user=SDLCOwner"
  "61-ai-sdlc-evidence::/mvp/ai-sdlc/evidence?role=ai_sdlc_owner&user=SDLCOwner"
  "62-ai-sdlc-findings::/mvp/ai-sdlc/findings?role=ai_sdlc_owner&user=SDLCOwner"
  "63-ai-sdlc-reports::/mvp/ai-sdlc/reports?role=ai_sdlc_owner&user=SDLCOwner"
  "64-ai-governance-posture::/mvp/ai-governance?role=ai_governance_owner&user=AIGovOwner"
  "65-ai-registry::/mvp/ai-registry?role=ai_governance_owner&user=AIGovOwner"
  "66-governance-quality::/mvp/governance-quality?role=admin&user=Admin"
)

for spec in "${SPECS[@]}"; do
  name="${spec%%::*}"; path="${spec#*::}"
  shoot "$name" "$path"
done
pkill -9 -f "headless=new" 2>/dev/null
echo "COMPLETE: $(ls -1 "$OUT"/*.png 2>/dev/null | wc -l | tr -d ' ') PNG files in $OUT"
