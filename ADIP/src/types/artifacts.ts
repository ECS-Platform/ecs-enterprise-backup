export type ApprovalStatus = 'Approved' | 'Pending Review' | 'Draft' | 'Rejected';

export type ArtifactFileType = 'docx' | 'xlsx' | 'yaml' | 'png';

export interface GenerationHistoryEntry {
  version: string;
  generatedDate: string;
  generatedBy: string;
  modelUsed: string;
  changeSummary: string;
}

export interface Artifact {
  id: string;
  name: string;
  generatedBy: string;
  modelUsed: string;
  version: string;
  generatedDate: string;
  approvalStatus: ApprovalStatus;
  fileType: ArtifactFileType;
  previewContent: string;
  generationHistory: GenerationHistoryEntry[];
}

export type GenerationRunStatus = 'Completed' | 'In Progress' | 'Failed';

export interface GenerationRun {
  runId: string;
  timestamp: string;
  generatedBy: string;
  status: GenerationRunStatus;
}
