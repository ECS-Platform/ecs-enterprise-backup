import type { Artifact } from '../types/artifacts';
import { createRunId, formatTimestamp } from './requirementArtifactFactory';

export { createRunId, formatTimestamp };

export interface ApprovedArtifactOption {
  id: string;
  label: string;
  feature: string;
}

export const approvedBrdOptions: ApprovedArtifactOption[] = [
  { id: 'brd-upi', label: 'BRD.docx — UPI Limit Enhancement', feature: 'UPI Limit Enhancement' },
  { id: 'brd-settlement', label: 'BRD.docx — Merchant Auto Settlement', feature: 'Merchant Auto Settlement' },
  { id: 'brd-biometric', label: 'BRD.docx — Biometric Login', feature: 'Biometric Login' },
];

export const approvedFrdOptions: ApprovedArtifactOption[] = [
  { id: 'frd-upi', label: 'FRD.docx — UPI Limit Enhancement', feature: 'UPI Limit Enhancement' },
  { id: 'frd-settlement', label: 'FRD.docx — Merchant Auto Settlement', feature: 'Merchant Auto Settlement' },
  { id: 'frd-mandate', label: 'FRD.docx — Recurring Mandate Upgrade', feature: 'Recurring Mandate Upgrade' },
];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function buildDesignArtifacts(brdId: string, frdId: string, runId: string): Artifact[] {
  const brd = approvedBrdOptions.find((o) => o.id === brdId);
  const frd = approvedFrdOptions.find((o) => o.id === frdId);
  const feature = brd?.feature || frd?.feature || 'System Feature';
  const date = today();

  return [
    {
      id: `${runId}-hld`,
      name: 'HLD.docx',
      generatedBy: 'Design AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Pending Review',
      fileType: 'docx',
      previewContent: `HIGH-LEVEL DESIGN
${feature}

1. System Context
   Derived from ${brd?.label || 'Approved BRD'}

2. Component Overview
   • API Gateway Layer
   • Core Banking Services
   • Notification & Event Bus
   • Compliance Audit Service

3. Integration Points
   NPCI Switch, Core Ledger, Merchant Portal`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Design AI', modelUsed: 'Gemini', changeSummary: `HLD from ${brd?.label}` },
      ],
    },
    {
      id: `${runId}-lld`,
      name: 'LLD.docx',
      generatedBy: 'Design AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'docx',
      previewContent: `LOW-LEVEL DESIGN
${feature}

Service: ${feature.replace(/\s+/g, '')}Service
  - LimitValidationHandler
  - SettlementOrchestrator
  - ComplianceAuditEmitter

Sequence: Request → Auth → Business Rules → Persistence → Event`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Design AI', modelUsed: 'Gemini', changeSummary: `LLD from ${frd?.label}` },
      ],
    },
    {
      id: `${runId}-api`,
      name: 'API_Specification.yaml',
      generatedBy: 'Design AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'yaml',
      previewContent: `openapi: 3.0.3
info:
  title: ${feature} API
  version: 1.0.0
paths:
  /v1/${feature.toLowerCase().replace(/\s+/g, '-')}:
    post:
      summary: Process ${feature}
      responses:
        '200':
          description: Success`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Design AI', modelUsed: 'Gemini', changeSummary: 'API spec from LLD service contracts' },
      ],
    },
    {
      id: `${runId}-db`,
      name: 'Database_Design.docx',
      generatedBy: 'Design AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'docx',
      previewContent: `DATABASE DESIGN
${feature}

Tables:
  • txn_limits (customer_id, tier, daily_cap, updated_at)
  • settlement_batches (merchant_id, amount, status, settled_at)
  • audit_events (entity_id, event_type, payload, created_at)

Indexes: customer_id, merchant_id, settled_at`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Design AI', modelUsed: 'Gemini', changeSummary: 'Data model from entity relationship analysis' },
      ],
    },
    {
      id: `${runId}-diagram`,
      name: 'Architecture_Diagram.png',
      generatedBy: 'Design AI',
      modelUsed: 'Gemini',
      version: '1.0',
      generatedDate: date,
      approvalStatus: 'Draft',
      fileType: 'png',
      previewContent: `[Architecture Diagram Preview]
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Client App │────▶│  API Gateway │────▶│ ${feature}  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                    ┌──────────────┐     ┌───────▼──────┐
                    │  Event Bus   │◀────│ Core Ledger  │
                    └──────────────┘     └──────────────┘`,
      generationHistory: [
        { version: '1.0', generatedDate: date, generatedBy: 'Design AI', modelUsed: 'Gemini', changeSummary: 'Diagram synthesized from HLD components' },
      ],
    },
  ];
}
