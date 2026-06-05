import { useMemo } from 'react';
import { useSimulation } from '../context/SimulationContext';
import { filterByDomain } from '../services/mockDataEngine.js';
import type { SimulationState } from '../types/simulation';

export function useFilteredSimulation() {
  const { state, selectedDomain } = useSimulation();

  return useMemo(() => {
    const domain = selectedDomain;
    const filtered = {
      ...state,
      dynamicInsights: state.dynamicInsights,
      executive: {
        ...state.executive,
        domainHealth:
          domain === 'all'
            ? state.executive.domainHealth
            : state.executive.domainHealth.filter((d) => {
                const map: Record<string, string> = {
                  netbanking: 'Net Banking',
                  mobile: 'Mobile Banking',
                  payments: 'Payments',
                };
                return d.name === map[domain];
              }),
        criticalIncidents: filterByDomain(state.executive.criticalIncidents, 'domain', domain) as typeof state.executive.criticalIncidents,
      },
      release: {
        ...state.release,
        releases: filterByDomain(state.release.releases, 'domain', domain) as typeof state.release.releases,
        riskMatrix: filterByDomain(state.release.riskMatrix, 'domain', domain) as typeof state.release.riskMatrix,
      },
      production: {
        ...state.production,
        openIncidents: filterByDomain(state.production.openIncidents, 'domain', domain) as typeof state.production.openIncidents,
      },
      requirements: {
        ...state.requirements,
        topRiskRequirements: filterByDomain(state.requirements.topRiskRequirements, 'domain', domain) as typeof state.requirements.topRiskRequirements,
      },
      delivery: {
        ...state.delivery,
        topRequirements: filterByDomain(state.delivery.topRequirements, 'domain', domain) as typeof state.delivery.topRequirements,
      },
    };
    return filtered as SimulationState;
  }, [state, selectedDomain]);
}
