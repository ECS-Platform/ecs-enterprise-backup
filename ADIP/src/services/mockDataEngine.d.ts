import type { SimulationState } from '../types/simulation';

export const DOMAINS: { id: string; label: string }[];
export const BANKING_DOMAINS: string[];

export interface PaymentChannelSeed {
  id: string;
  name: string;
  weight: number;
  basePeakTps: number;
  volatility: number;
  incidentBias: number;
  dependsOn: string[];
  timeProfile: number[];
}

export const PAYMENT_CHANNELS: PaymentChannelSeed[];

export interface IncidentSeed {
  id: string;
  title: string;
  domain: string;
  channel?: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
}

export const INCIDENT_CATALOG_FULL: IncidentSeed[];

export interface GovernanceSeed {
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
}

export const GOVERNANCE_CATALOG_FULL: GovernanceSeed[];

export function createInitialState(): SimulationState;
export function filterByDomain(
  items: unknown[],
  domainKey?: string,
  filter?: string,
): unknown[];

export function clamp(n: number, min: number, max: number): number;
export function sparkline7d(base?: number): { day: string; value: number }[];
