export type SummaryPriority = 'P0' | 'P1' | 'P2';
export type SummarySeverity = 'critical' | 'high' | 'medium' | 'low';
export type HealthBand = 'Healthy' | 'Watch' | 'Attention';

export interface HealthBreakdownEntry {
  name: string;
  value: number;
  status: HealthBand;
}

export interface RiskItem {
  title: string;
  severity: SummarySeverity;
  impact: string;
  source: string;
}

export interface IncidentItem {
  id: string;
  title: string;
  domain: string;
  severity: SummarySeverity;
  duration: string;
  status: string;
}

export interface ReleaseItem {
  id: string;
  name: string;
  domain: string;
  confidence: number;
  risk: SummarySeverity;
}

export interface ActionItem {
  priority: SummaryPriority;
  action: string;
  owner: string;
}

export interface ExecutiveSummary {
  generatedAt: string;
  simulationTick: number;
  simulatedTime: string;
  headline: string;
  overallHealthScore: {
    score: number;
    label: HealthBand;
    narrative: string;
    breakdown: HealthBreakdownEntry[];
  };
  keyRisks: {
    narrative: string;
    items: RiskItem[];
  };
  keyAchievements: {
    narrative: string;
    items: string[];
  };
  criticalIncidents: {
    narrative: string;
    items: IncidentItem[];
  };
  releaseStatus: {
    narrative: string;
    goNoGo: string;
    confidence: number;
    items: ReleaseItem[];
  };
  governanceStatus: {
    narrative: string;
    score: number;
    bullets: string[];
  };
  recommendedActions: {
    narrative: string;
    items: ActionItem[];
  };
}
