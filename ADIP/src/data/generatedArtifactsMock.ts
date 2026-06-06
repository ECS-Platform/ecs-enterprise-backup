export type ApprovalStatus = 'Approved' | 'Pending Review' | 'Draft' | 'Rejected';

export interface GenerationHistoryEntry {
  version: string;
  generatedDate: string;
  generatedBy: string;
  modelUsed: string;
  changeSummary: string;
}

export interface GeneratedArtifact {
  id: string;
  name: string;
  generatedBy: string;
  modelUsed: string;
  version: string;
  generatedDate: string;
  approvalStatus: ApprovalStatus;
  fileType: 'docx' | 'xlsx';
  previewContent: string;
  generationHistory: GenerationHistoryEntry[];
}

export const generatedArtifacts: GeneratedArtifact[] = [
  {
    id: 'artifact-brd',
    name: 'BRD.docx',
    generatedBy: 'Requirement AI',
    modelUsed: 'Gemini',
    version: '1.2',
    generatedDate: '2025-06-04',
    approvalStatus: 'Approved',
    fileType: 'docx',
    previewContent: `BUSINESS REQUIREMENTS DOCUMENT
UPI Limit Enhancement Initiative

1. Executive Summary
   Enable tiered UPI transaction limits for verified retail customers,
   increasing daily caps from ₹1L to ₹2L for KYC Level 2 accounts.

2. Business Objectives
   • Reduce limit-related support tickets by 35%
   • Improve merchant settlement velocity
   • Maintain RBI compliance for retail payment limits

3. Stakeholders
   Product Owner: Retail Payments
   Sponsor: Head of Digital Banking`,
    generationHistory: [
      { version: '1.2', generatedDate: '2025-06-04', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Final review — compliance section updated' },
      { version: '1.1', generatedDate: '2025-06-02', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Added stakeholder matrix and success metrics' },
      { version: '1.0', generatedDate: '2025-05-28', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Initial generation from analysis queue input' },
    ],
  },
  {
    id: 'artifact-frd',
    name: 'FRD.docx',
    generatedBy: 'Requirement AI',
    modelUsed: 'Gemini',
    version: '2.0',
    generatedDate: '2025-06-03',
    approvalStatus: 'Pending Review',
    fileType: 'docx',
    previewContent: `FUNCTIONAL REQUIREMENTS DOCUMENT
Merchant Auto Settlement — Phase 2

FR-001: Settlement Trigger
  System shall initiate T+1 settlement when merchant daily volume exceeds ₹50,000.

FR-002: Notification Service
  Push and SMS alerts sent within 30 seconds of settlement completion.

FR-003: Reconciliation
  NEFT/RTGS reference IDs mapped to merchant ledger entries automatically.`,
    generationHistory: [
      { version: '2.0', generatedDate: '2025-06-03', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Regenerated with updated settlement rules' },
      { version: '1.0', generatedDate: '2025-05-30', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Initial functional spec draft' },
    ],
  },
  {
    id: 'artifact-user-stories',
    name: 'UserStories.xlsx',
    generatedBy: 'Requirement AI',
    modelUsed: 'Gemini',
    version: '1.3',
    generatedDate: '2025-06-05',
    approvalStatus: 'Approved',
    fileType: 'xlsx',
    previewContent: `Sheet: User Stories

| ID       | Epic              | Story                                      | Points |
|----------|-------------------|--------------------------------------------|--------|
| US-1042  | UPI Limits        | As a customer, I want to view my tier...   | 3      |
| US-1043  | UPI Limits        | As a customer, I want to request limit...  | 5      |
| US-1044  | Auto Settlement   | As a merchant, I want T+1 settlement...    | 8      |
| US-1045  | Auto Settlement   | As ops, I want a reconciliation dashboard  | 5      |`,
    generationHistory: [
      { version: '1.3', generatedDate: '2025-06-05', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Added acceptance criteria column per story' },
      { version: '1.2', generatedDate: '2025-06-01', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Story point estimates refined' },
      { version: '1.0', generatedDate: '2025-05-29', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Initial story breakdown from BRD' },
    ],
  },
  {
    id: 'artifact-acceptance-criteria',
    name: 'AcceptanceCriteria.docx',
    generatedBy: 'Requirement AI',
    modelUsed: 'Gemini',
    version: '1.0',
    generatedDate: '2025-06-05',
    approvalStatus: 'Draft',
    fileType: 'docx',
    previewContent: `ACCEPTANCE CRITERIA
UPI Limit Enhancement & Merchant Settlement

AC-001: Limit Tier Display
  GIVEN a KYC Level 2 customer
  WHEN they open the UPI settings screen
  THEN their current limit tier and daily cap are displayed

AC-002: Settlement Confirmation
  GIVEN a merchant with eligible volume
  WHEN T+1 settlement completes
  THEN a confirmation is sent via push and SMS within 30s`,
    generationHistory: [
      { version: '1.0', generatedDate: '2025-06-05', generatedBy: 'Requirement AI', modelUsed: 'Gemini', changeSummary: 'Initial acceptance criteria from user stories' },
    ],
  },
];
