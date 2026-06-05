export interface SparkPoint {
  day: string;
  value: number;
}

export interface DomainHealth {
  name: string;
  score: number;
  changes: number;
  risks: number;
  incidents: number;
  trend: SparkPoint[];
}

export interface PaymentChannelSnapshot {
  id: string;
  name: string;
  weight: number;
  health: number;
  tps: number;
  successRate: number;
  latencyMs: number;
  openIncidents: number;
  load: number;
}

export interface PaymentsRollup {
  channels: PaymentChannelSnapshot[];
  aggregateHealth: number;
  totalTps: number;
  criticalChannels: number;
}

export interface SimulationState {
  tick: number;
  lastUpdated: string;
  selectedDomain: string;
  payments?: PaymentsRollup;
  executive: {
    kpis: { label: string; value: number; trend: number; data: SparkPoint[] }[];
    openRisks: number;
    openIncidents: number;
    businessImpactScore: number;
    portfolioHealth: number;
    domainHealth: DomainHealth[];
    portfolioMetrics: { label: string; value: number; trend: number }[];
    riskByPhase: { name: string; value: number; color: string }[];
    businessImpactAreas: { name: string; value: number }[];
    confidenceTrend: { month: string; net: number; mobile: number; payments: number }[];
    criticalIncidents: { id: string; title: string; domain: string; severity: string; duration: string; status: string }[];
    scorecard: { label: string; value: number }[];
    activeScans: { name: string; progress: number; status: string }[];
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  delivery: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  requirements: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  architecture: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  development: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  testing: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  release: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  production: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  operations: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  governance: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  learning: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  reports: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  administration: any;
  dynamicInsights: string[];
  previous: Record<string, number>;
  aiSuggestedQuestions: string[];
}
