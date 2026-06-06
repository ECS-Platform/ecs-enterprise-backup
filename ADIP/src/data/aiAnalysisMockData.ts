export type AnalysisPhase =
  | 'requirements'
  | 'architecture'
  | 'design'
  | 'development'
  | 'testing'
  | 'deployment';

export interface PhaseConfig {
  agents: string[];
  glow: 'blue' | 'purple' | 'green' | 'none';
  runningTitle: string;
  completeTitle: string;
  subtitle: string;
  progressMessages: string[];
}

export const PHASE_CONFIG: Record<AnalysisPhase, PhaseConfig> = {
  requirements: {
    agents: ['Requirement Agent', 'Risk Agent', 'Compliance Agent', 'Business Analyst Agent'],
    glow: 'purple',
    runningTitle: 'Requirements Analysis Running',
    completeTitle: 'Requirements Analysis Complete',
    subtitle: 'Requirements phase · business & compliance review',
    progressMessages: [
      'Parsing business requirements and stakeholder intent...',
      'Assessing delivery and operational risk factors...',
      'Mapping regulatory and compliance obligations...',
      'Synthesising acceptance criteria and gap analysis...',
    ],
  },
  architecture: {
    agents: ['Architecture Agent', 'Integration Agent', 'Data Design Agent', 'Security Agent'],
    glow: 'blue',
    runningTitle: 'Architecture Analysis Running',
    completeTitle: 'Architecture Analysis Complete',
    subtitle: 'Architecture phase · system topology review',
    progressMessages: [
      'Evaluating architectural patterns and system boundaries...',
      'Tracing cross-service integration dependencies...',
      'Reviewing data flow and persistence design...',
      'Assessing security posture across service layers...',
    ],
  },
  design: {
    agents: [
      'Solution Design Agent',
      'Integration Design Agent',
      'Data Model Agent',
      'Security Design Agent',
    ],
    glow: 'blue',
    runningTitle: 'Design Analysis Running',
    completeTitle: 'Design Analysis Complete',
    subtitle: 'Design phase · solution & integration blueprint',
    progressMessages: [
      'Drafting high-level solution design recommendations...',
      'Identifying integration points across banking platforms...',
      'Modelling data entities and relationship contracts...',
      'Conducting security design review and threat modelling...',
    ],
  },
  development: {
    agents: [
      'API Design Agent',
      'Service Design Agent',
      'Database Design Agent',
      'Code Review Agent',
    ],
    glow: 'purple',
    runningTitle: 'Development Analysis Running',
    completeTitle: 'Development Analysis Complete',
    subtitle: 'Development phase · build readiness assessment',
    progressMessages: [
      'Defining API components and endpoint contracts...',
      'Structuring service components and dependencies...',
      'Analysing database schema changes and migrations...',
      'Running code review and development readiness checks...',
    ],
  },
  testing: {
    agents: ['Test Planning Agent', 'Test Case Agent', 'Regression Agent', 'Coverage Agent'],
    glow: 'green',
    runningTitle: 'Testing Analysis Running',
    completeTitle: 'Testing Analysis Complete',
    subtitle: 'Testing phase · quality assurance planning',
    progressMessages: [
      'Building test strategy and scenario coverage plan...',
      'Generating detailed test cases from requirements...',
      'Assembling regression pack for impacted modules...',
      'Calculating coverage gaps and quality summary...',
    ],
  },
  deployment: {
    agents: [
      'Release Planning Agent',
      'Deployment Agent',
      'Rollback Agent',
      'Validation Agent',
    ],
    glow: 'green',
    runningTitle: 'Deployment Analysis Running',
    completeTitle: 'Deployment Analysis Complete',
    subtitle: 'Deployment phase · release & go-live readiness',
    progressMessages: [
      'Compiling release notes and change documentation...',
      'Drafting step-by-step deployment runbook...',
      'Validating rollback procedures and recovery paths...',
      'Building go-live validation checklist...',
    ],
  },
};

export type AnalysisResult = Record<string, string | number | string[]>;

function seedFromText(text: string): number {
  return text.split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0) || 42;
}

function pick<T>(items: T[], seed: number, offset = 0): T {
  return items[(seed + offset) % items.length];
}

export function generateAnalysisResult(phase: AnalysisPhase, inputText: string): AnalysisResult {
  const seed = seedFromText(inputText.trim() || phase);
  const topic = inputText.trim() || `${phase} scope`;

  switch (phase) {
    case 'requirements':
      return {
        Domain: pick(['Payments', 'Lending', 'Core Banking', 'Wealth Management'], seed),
        Complexity: pick(['Low', 'Medium', 'High', 'Very High'], seed, 1),
        Risk: pick(['Low', 'Medium', 'High', 'Critical'], seed, 2),
        'Compliance Mapping': pick(
          ['RBI UPI Guidelines', 'PCI-DSS Level 1', 'SEBI MF Regulations', 'AML/KYC Framework'],
          seed,
          3,
        ),
        'Missing Information': [
          'Non-functional performance targets',
          'Rollback and exception handling rules',
          'Stakeholder sign-off criteria',
        ],
        'Suggested Acceptance Criteria': [
          `Validate end-to-end flow for "${topic}" under peak load`,
          'Confirm audit trail and regulatory reporting coverage',
          'Verify error handling for downstream dependency failures',
        ],
        'Confidence Score': 72 + (seed % 23),
      };

    case 'architecture':
      return {
        'Recommended Pattern': pick(
          ['Event-Driven Microservices', 'Modular Monolith', 'CQRS + Saga', 'API Gateway + BFF'],
          seed,
        ),
        Dependencies: [
          'Payment Switch',
          'Core Ledger Service',
          'Notification Hub',
          'Fraud Detection Engine',
        ],
        Risks: [
          'Cross-service transaction consistency',
          'Legacy adapter latency under burst traffic',
          'Schema drift across integration contracts',
        ],
        'Architecture Score': 68 + (seed % 27),
        'Recommended Components': [
          'API Gateway with rate limiting',
          'Event bus for async settlement',
          'Read replica for reporting queries',
        ],
      };

    case 'design':
      return {
        'Security Review': pick(
          ['Pass with minor findings', 'Conditional pass — encryption gaps', 'Pass — controls aligned', 'Review required — PII exposure risk'],
          seed,
        ),
        'Design Score': 74 + (seed % 21),
        'HLD Recommendations': [
          `Layered service architecture for "${topic}"`,
          'Event-driven settlement orchestration layer',
          'Dedicated compliance audit sidecar',
        ],
        'Integration Points': [
          'NPCI UPI Switch',
          'Core Banking Ledger API',
          'Merchant Notification Gateway',
          'Fraud Scoring Engine',
        ],
        'Data Entities': [
          'Transaction',
          'SettlementBatch',
          'MerchantAccount',
          'ComplianceAuditLog',
        ],
      };

    case 'development':
      return {
        'Development Readiness': pick(
          ['Ready to build', 'Ready with minor gaps', 'Blocked — API contract pending', 'In progress — schema review needed'],
          seed,
        ),
        'Readiness Score': 70 + (seed % 25),
        'API Components': [
          'POST /v1/settlements',
          'GET /v1/merchants/{id}/limits',
          'PATCH /v1/transactions/{id}/status',
        ],
        'Service Components': [
          `${topic.replace(/\s+/g, '')}Orchestrator`,
          'LimitValidationService',
          'SettlementReconciliationWorker',
        ],
        'Database Changes': [
          'Add settlement_batch table with partitioning',
          'Index on merchant_id + transaction_date',
          'Migration for limit_history audit trail',
        ],
      };

    case 'testing':
      return {
        'Coverage Summary': pick(
          ['82% line coverage — 3 gaps in payment flow', '76% coverage — regression pack needed for settlement', '88% coverage — strong API test depth', '71% coverage — manual scenarios required'],
          seed,
        ),
        'Coverage Score': 68 + (seed % 28),
        'Test Scenarios': [
          `End-to-end "${topic}" happy path`,
          'Concurrent settlement under peak load',
          'Downstream dependency failure recovery',
        ],
        'Test Cases': [
          'TC-001: Validate UPI limit enforcement',
          'TC-002: Settlement batch reconciliation',
          'TC-003: Merchant notification on failure',
        ],
        'Regression Pack': [
          'Core payment smoke suite',
          'Settlement regression v2.4',
          'Merchant portal integration tests',
        ],
      };

    case 'deployment':
      return {
        'Go-Live Status': pick(
          ['Green — proceed to production', 'Amber — staged rollout recommended', 'Green — canary deployment advised', 'Amber — rollback drill required'],
          seed,
        ),
        'Release Confidence': 75 + (seed % 20),
        'Release Notes': [
          `Feature: ${topic}`,
          'Settlement orchestration performance improvements',
          'Security patch for API gateway rate limiting',
        ],
        'Deployment Plan': [
          'Deploy API gateway config to staging',
          'Run database migration in maintenance window',
          'Progressive traffic shift — 10% → 50% → 100%',
        ],
        'Rollback Plan': [
          'Revert gateway routing to previous version',
          'Restore database snapshot pre-migration',
          'Disable feature flag and drain in-flight requests',
        ],
        'Go-Live Checklist': [
          'Smoke tests passed in production',
          'Monitoring dashboards configured',
          'On-call roster confirmed',
          'Stakeholder sign-off received',
        ],
      };
  }
}
