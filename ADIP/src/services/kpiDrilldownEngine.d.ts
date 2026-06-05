import type { KpiDrilldownContext, KpiDrilldownPayload } from '../types/kpiDrilldown';
import type { SimulationState } from '../types/simulation';

export function resolveKpiDrilldown(
  ctx: KpiDrilldownContext,
  state: SimulationState,
): KpiDrilldownPayload;
