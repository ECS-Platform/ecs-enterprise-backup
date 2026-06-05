import type { SparkPoint } from './simulation';

export interface KpiDrilldownRecord {
  id: string;
  title: string;
  detail?: string;
  meta?: string;
}

export interface KpiDrilldownApplication {
  name: string;
  status?: string;
}

export interface KpiDrilldownIncident {
  id: string;
  title: string;
  severity: string;
  domain?: string;
}

export interface KpiDrilldownRelease {
  id: string;
  name: string;
  confidence: number;
  risk: string;
}

export interface KpiDrilldownPayload {
  label: string;
  value: string | number;
  suffix?: string;
  sourceRecords: KpiDrilldownRecord[];
  supportingEvidence: string[];
  relatedApplications: KpiDrilldownApplication[];
  relatedIncidents: KpiDrilldownIncident[];
  relatedReleases: KpiDrilldownRelease[];
  historicalTrend: SparkPoint[];
}

export interface KpiDrilldownContext {
  label: string;
  value: string | number;
  suffix?: string;
  trend?: number;
  data?: SparkPoint[];
}
