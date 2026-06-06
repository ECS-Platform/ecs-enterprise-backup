import type { Artifact } from '../types/artifacts';
import { createRunId, formatTimestamp } from './requirementArtifactFactory';

export { createRunId, formatTimestamp };

export interface ApprovedDevOption {
  id: string;
  label: string;
  feature: string;
}

export const approvedApiSpecOptions: ApprovedDevOption[] = [
  { id: 'api-upi', label: 'API_Specification.yaml — UPI Limit Enhancement', feature: 'UPI Limit Enhancement' },
  { id: 'api-settlement', label: 'API_Specification.yaml — Merchant Auto Settlement', feature: 'Merchant Auto Settlement' },
  { id: 'api-biometric', label: 'API_Specification.yaml — Biometric Login', feature: 'Biometric Login' },
];

export const approvedServiceDesignOptions: ApprovedDevOption[] = [
  { id: 'svc-upi', label: 'Service_Design.docx — UPI Limit Enhancement', feature: 'UPI Limit Enhancement' },
  { id: 'svc-settlement', label: 'Service_Design.docx — Merchant Auto Settlement', feature: 'Merchant Auto Settlement' },
  { id: 'svc-mandate', label: 'Service_Design.docx — Recurring Mandate Upgrade', feature: 'Recurring Mandate Upgrade' },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function buildTestingArtifacts(apiId: string, serviceId: string, runId: string): Artifact[] {
  const api = approvedApiSpecOptions.find((o) => o.id === apiId);
  const service = approvedServiceDesignOptions.find((o) => o.id === serviceId);
  const feature = api?.feature || service?.feature || 'System Feature';
  const date = today();

  return [
    {
      id: `${runId}-scenarios`,
      name: 'Test_Scenarios.docx',
      generatedBy: 'Testing AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Pending Review',
      fileType: 'docx',
      previewContent: `TEST SCENARIOS
${feature}

TS-001: Happy Path
  Validate end-to-end ${feature} flow with valid inputs.

TS-002: Boundary Conditions
  Test daily limits, timeout handling, and retry semantics.

TS-003: Compliance & Audit
  Verify audit trail and regulatory event emission.

TS-004: Negative Scenarios
  Invalid payloads, auth failures, and downstream unavailability.

Source: ${api?.label || 'Approved API Specification'}`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Testing AI', modelUsed: 'Gemini', changeSummary: `Scenarios from ${api?.label}` },
      ],
    },
    {
      id: `${runId}-cases`,
      name: 'Test_Cases.xlsx',
      generatedBy: 'Testing AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'xlsx',
      previewContent: `Sheet: Test Cases — ${feature}

| ID     | Scenario        | Steps                          | Expected Result           | Priority |
|--------|-----------------|--------------------------------|---------------------------|----------|
| TC-001 | Valid request   | Submit valid ${feature} payload| 200 OK, txn recorded      | P1       |
| TC-002 | Limit exceeded  | Submit over-limit amount       | 400 with limit error code | P1       |
| TC-003 | Auth failure    | Submit without valid token     | 401 Unauthorized          | P2       |
| TC-004 | Audit trail     | Complete successful txn        | Audit event published     | P1       |`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Testing AI', modelUsed: 'Gemini', changeSummary: `Cases derived from test scenarios — ${feature}` },
      ],
    },
    {
      id: `${runId}-regression`,
      name: 'Regression_Suite.xlsx',
      generatedBy: 'Testing AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'xlsx',
      previewContent: `Sheet: Regression Suite — ${feature}

| Suite ID | Name                    | Cases | Automation | Environment |
|----------|-------------------------|-------|------------|-------------|
| RS-001   | Core ${feature} Smoke   | 12    | 80%        | SIT         |
| RS-002   | Payment Edge Cases      | 18    | 65%        | UAT         |
| RS-003   | Compliance Regression   | 8     | 90%        | Pre-Prod    |

Source: ${service?.label || 'Approved Service Design'}`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Testing AI', modelUsed: 'Gemini', changeSummary: `Regression pack from ${service?.label}` },
      ],
    },
    {
      id: `${runId}-coverage`,
      name: 'Coverage_Report.docx',
      generatedBy: 'Testing AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'docx',
      previewContent: `COVERAGE REPORT
${feature}

Overall Coverage: 87.4%
  • API Endpoints: 94%
  • Business Rules: 85%
  • Error Paths: 78%
  • Compliance Flows: 92%

Gaps Identified:
  1. Retry logic on downstream timeout (TC-015 missing)
  2. Concurrent limit update race condition
  3. Mandate expiry edge case

Recommendation: Add 6 cases to close P1 gaps before release.`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Testing AI', modelUsed: 'Gemini', changeSummary: `Coverage analysis for ${feature} test suite` },
      ],
    },
  ];
}
