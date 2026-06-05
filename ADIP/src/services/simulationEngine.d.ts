import type { SimulationState } from '../types/simulation';

export function getRefreshInterval(): number;
export function tickSimulation(state: SimulationState): SimulationState;
export function startSimulation(onTick: (state: SimulationState) => void): () => void;
export function stopSimulation(): void;
export function forceTick(state: SimulationState): SimulationState;
export function generateExecutiveInsights(
  prev: Record<string, number>,
  current: Record<string, number>,
): string[];
