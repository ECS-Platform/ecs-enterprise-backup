import type { Artifact } from '../types/artifacts';
import { createRunId, formatTimestamp } from './requirementArtifactFactory';

export { createRunId, formatTimestamp };

export interface ApprovedDesignOption {
  id: string;
  label: string;
  feature: string;
}

export const approvedHldOptions: ApprovedDesignOption[] = [
  { id: 'hld-upi', label: 'HLD.docx — UPI Limit Enhancement', feature: 'UPI Limit Enhancement' },
  { id: 'hld-settlement', label: 'HLD.docx — Merchant Auto Settlement', feature: 'Merchant Auto Settlement' },
  { id: 'hld-biometric', label: 'HLD.docx — Biometric Login', feature: 'Biometric Login' },
];

export const approvedLldOptions: ApprovedDesignOption[] = [
  { id: 'lld-upi', label: 'LLD.docx — UPI Limit Enhancement', feature: 'UPI Limit Enhancement' },
  { id: 'lld-settlement', label: 'LLD.docx — Merchant Auto Settlement', feature: 'Merchant Auto Settlement' },
  { id: 'lld-mandate', label: 'LLD.docx — Recurring Mandate Upgrade', feature: 'Recurring Mandate Upgrade' },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function buildDevelopmentArtifacts(hldId: string, lldId: string, runId: string): Artifact[] {
  const hld = approvedHldOptions.find((o) => o.id === hldId);
  const lld = approvedLldOptions.find((o) => o.id === lldId);
  const feature = hld?.feature || lld?.feature || 'System Feature';
  const serviceName = feature.replace(/\s+/g, '');
  const date = today();

  return [
    {
      id: `${runId}-api`,
      name: 'API_Specification.yaml',
      generatedBy: 'Development AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Pending Review',
      fileType: 'yaml',
      previewContent: `openapi: 3.0.3
info:
  title: ${feature} API
  version: 1.0.0
paths:
  /v1/${feature.toLowerCase().replace(/\s+/g, '-')}:
    post:
      summary: Process ${feature}
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: Success
        '400':
          description: Validation error`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Development AI', modelUsed: 'Gemini', changeSummary: `API spec from ${hld?.label}` },
      ],
    },
    {
      id: `${runId}-service`,
      name: 'Service_Design.docx',
      generatedBy: 'Development AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'docx',
      previewContent: `SERVICE DESIGN
${feature}

Service: ${serviceName}Service
Package: com.bank.payments.${serviceName.toLowerCase()}

Components:
  • ${serviceName}Controller — REST endpoints
  • ${serviceName}Service — business logic orchestration
  • ${serviceName}Repository — persistence layer
  • ComplianceAuditEmitter — regulatory event publishing

Derived from: ${lld?.label || 'Approved LLD'}`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Development AI', modelUsed: 'Gemini', changeSummary: `Service design from ${lld?.label}` },
      ],
    },
    {
      id: `${runId}-db`,
      name: 'Database_Scripts.sql',
      generatedBy: 'Development AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'yaml',
      previewContent: `-- Database Scripts: ${feature}
-- Generated from ${hld?.label || 'Approved HLD'}

CREATE TABLE IF NOT EXISTS ${serviceName.toLowerCase()}_txn (
  id            UUID PRIMARY KEY,
  customer_id   VARCHAR(32) NOT NULL,
  amount        DECIMAL(18,2) NOT NULL,
  status        VARCHAR(16) NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_${serviceName.toLowerCase()}_customer
  ON ${serviceName.toLowerCase()}_txn (customer_id);`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Development AI', modelUsed: 'Gemini', changeSummary: 'DDL scripts from data model design' },
      ],
    },
    {
      id: `${runId}-code`,
      name: 'Code_Package.zip',
      generatedBy: 'Development AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'xlsx',
      previewContent: `Code Package: ${feature}

src/main/java/com/bank/payments/${serviceName.toLowerCase()}/
  ├── ${serviceName}Application.java
  ├── controller/${serviceName}Controller.java
  ├── service/${serviceName}Service.java
  ├── repository/${serviceName}Repository.java
  └── model/${serviceName}Entity.java

tests/
  ├── ${serviceName}ServiceTest.java
  └── ${serviceName}ControllerTest.java

Build: Maven 3.9 · Java 17 · Spring Boot 3.2`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Development AI', modelUsed: 'Gemini', changeSummary: `Scaffolded from service design — ${feature}` },
      ],
    },
  ];
}
