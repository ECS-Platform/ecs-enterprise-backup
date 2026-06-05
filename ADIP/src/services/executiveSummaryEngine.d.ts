import type { SimulationState } from '../types/simulation';
import type { ExecutiveSummary } from '../types/executiveSummary';

export function generateExecutiveSummary(state: SimulationState): ExecutiveSummary;
export function formatSummaryAsText(summary: ExecutiveSummary): string;
