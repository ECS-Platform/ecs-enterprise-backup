import type { SimulationState } from '../types/simulation';

export const DOMAINS: { id: string; label: string }[];
export const BANKING_DOMAINS: string[];

export function createInitialState(): SimulationState;
export function filterByDomain(
  items: unknown[],
  domainKey?: string,
  filter?: string,
): unknown[];
