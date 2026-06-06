export type AnalysisPhase = 'requirements' | 'architecture';

export interface PhaseConfig {
  agents: string[];
  glow: 'blue' | 'purple' | 'green' | 'none';
}

export const PHASE_CONFIG: Record<AnalysisPhase, PhaseConfig> = {
  requirements: {
    agents: ['Requirement Agent', 'Risk Agent', 'Compliance Agent', 'Business Analyst Agent'],
    glow: 'purple',
  },
  architecture: {
    agents: ['Architecture Agent', 'Integration Agent', 'Data Design Agent', 'Security Agent'],
    glow: 'blue',
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
  }
}
