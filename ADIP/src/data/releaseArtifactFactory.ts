import type { Artifact } from '../types/artifacts';
import { createRunId, formatTimestamp } from './requirementArtifactFactory';

export { createRunId, formatTimestamp };

export interface ApprovedTestOption {
  id: string;
  label: string;
  feature: string;
}

export interface ReleaseIntake {
  releaseVersion: string;
  targetEnvironment: string;
  regressionSuiteId: string;
}

export const approvedRegressionOptions: ApprovedTestOption[] = [
  { id: 'reg-upi', label: 'Regression_Suite.xlsx — UPI Limit Enhancement', feature: 'UPI Limit Enhancement' },
  { id: 'reg-settlement', label: 'Regression_Suite.xlsx — Merchant Auto Settlement', feature: 'Merchant Auto Settlement' },
  { id: 'reg-mandate', label: 'Regression_Suite.xlsx — Recurring Mandate Upgrade', feature: 'Recurring Mandate Upgrade' },
];

export const targetEnvironmentOptions = [
  { value: 'sit', label: 'SIT' },
  { value: 'uat', label: 'UAT' },
  { value: 'preprod', label: 'Pre-Production' },
  { value: 'prod', label: 'Production' },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function buildReleaseArtifacts(intake: ReleaseIntake, runId: string): Artifact[] {
  const regression = approvedRegressionOptions.find((o) => o.id === intake.regressionSuiteId);
  const feature = regression?.feature || 'System Release';
  const version = intake.releaseVersion || 'v1.0.0';
  const env = intake.targetEnvironment
    ? targetEnvironmentOptions.find((o) => o.value === intake.targetEnvironment)?.label || intake.targetEnvironment
    : 'Production';
  const date = today();

  return [
    {
      id: `${runId}-notes`,
      name: 'Release_Notes.docx',
      generatedBy: 'Release AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Pending Review',
      fileType: 'docx',
      previewContent: `RELEASE NOTES
${version} — ${feature}

What's New:
  • ${feature} production rollout
  • Enhanced compliance audit trail
  • Performance improvements for peak-hour traffic

Bug Fixes:
  • Resolved timeout on settlement batch processing
  • Fixed duplicate notification on retry

Known Issues:
  • Legacy merchant portal shows stale cache for 5 min post-deploy`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Release AI', modelUsed: 'Gemini', changeSummary: `Release notes for ${version}` },
      ],
    },
    {
      id: `${runId}-deploy`,
      name: 'Deployment_Plan.docx',
      generatedBy: 'Release AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'docx',
      previewContent: `DEPLOYMENT PLAN
${version} → ${env}

Phase 1: Pre-Deployment (T-24h)
  • Freeze code branch release/${version}
  • Validate ${regression?.label || 'approved regression suite'}
  • Confirm infra capacity and DB migration scripts

Phase 2: Deployment (T-0)
  • Blue-green switch for ${feature} services
  • Run smoke tests (RS-001)
  • Enable feature flag at 10% traffic

Phase 3: Post-Deployment (T+2h)
  • Monitor error rates and latency SLOs
  • Ramp traffic to 100%
  • Sign off go-live checklist`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Release AI', modelUsed: 'Gemini', changeSummary: `Deployment plan for ${env}` },
      ],
    },
    {
      id: `${runId}-rollback`,
      name: 'Rollback_Plan.docx',
      generatedBy: 'Release AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'docx',
      previewContent: `ROLLBACK PLAN
${version} — ${feature}

Trigger Conditions:
  • Error rate > 2% for 15 minutes
  • P99 latency > 3s sustained
  • Critical compliance audit failure

Rollback Steps:
  1. Disable feature flag immediately
  2. Switch traffic to previous blue environment
  3. Revert DB migration (scripts/rollback_${version}.sql)
  4. Notify stakeholders and incident channel
  5. Run regression smoke on previous version

RTO: 30 minutes · RPO: 0 (no data loss on rollback)`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Release AI', modelUsed: 'Gemini', changeSummary: `Rollback plan for ${version}` },
      ],
    },
    {
      id: `${runId}-checklist`,
      name: 'Go_Live_Checklist.xlsx',
      generatedBy: 'Release AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'xlsx',
      previewContent: `Sheet: Go-Live Checklist — ${version}

| #  | Item                              | Owner       | Status    |
|----|-----------------------------------|-------------|-----------|
| 1  | Regression suite passed           | QA Lead     | Complete  |
| 2  | Security scan cleared             | SecOps      | Complete  |
| 3  | Change advisory board approved    | Release Mgr | Pending   |
| 4  | Monitoring dashboards configured  | SRE         | Complete  |
| 5  | Rollback drill completed          | DevOps      | Complete  |
| 6  | Stakeholder comms sent            | PMO         | Pending   |

Target: ${env} · Feature: ${feature}`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Release AI', modelUsed: 'Gemini', changeSummary: `Go-live checklist for ${version} → ${env}` },
      ],
    },
  ];
}
