import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';
import { createInitialState } from '../services/mockDataEngine.js';
import { startSimulation, forceTick, getRefreshInterval } from '../services/simulationService.js';
import { generateAIResponse } from '../services/aiResponseEngine.js';
import { resolveKpiDrilldown } from '../services/kpiDrilldownEngine.js';

import type { SimulationState } from '../types/simulation';
import type { KpiDrilldownContext, KpiDrilldownPayload } from '../types/kpiDrilldown';

type SimState = SimulationState;

interface QuerySession {
  question: string;
  answer: string;
}

interface KpiDrilldownState {
  context: KpiDrilldownContext;
  payload: KpiDrilldownPayload;
}

interface SimulationContextValue {
  state: SimState;
  selectedDomain: string;
  setSelectedDomain: (domain: string) => void;
  refreshNow: () => void;
  refreshIntervalMs: number;
  querySession: QuerySession | null;
  askQuestion: (question: string) => void;
  clearQuery: () => void;
  kpiDrilldown: KpiDrilldownState | null;
  openKpiDrilldown: (context: KpiDrilldownContext) => void;
  closeKpiDrilldown: () => void;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

export function SimulationProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SimState>(() => createInitialState());
  const stateRef = useRef(state);
  stateRef.current = state;
  const [selectedDomain, setSelectedDomain] = useState('all');
  const [querySession, setQuerySession] = useState<QuerySession | null>(null);
  const [kpiDrilldown, setKpiDrilldown] = useState<KpiDrilldownState | null>(null);

  useEffect(() => {
    const stop = startSimulation((next: SimulationState) => setState(next));
    return stop;
  }, []);

  const refreshNow = useCallback(() => {
    setState((prev: SimulationState) => forceTick(prev));
  }, []);

  const askQuestion = useCallback((question: string) => {
    const trimmed = question.trim();
    if (!trimmed) return;
    setQuerySession({
      question: trimmed,
      answer: generateAIResponse(trimmed, stateRef.current),
    });
  }, []);

  const clearQuery = useCallback(() => setQuerySession(null), []);

  const openKpiDrilldown = useCallback((context: KpiDrilldownContext) => {
    setKpiDrilldown({
      context,
      payload: resolveKpiDrilldown(context, stateRef.current),
    });
  }, []);

  const closeKpiDrilldown = useCallback(() => setKpiDrilldown(null), []);

  return (
    <SimulationContext.Provider
      value={{
        state,
        selectedDomain,
        setSelectedDomain,
        refreshNow,
        refreshIntervalMs: getRefreshInterval(),
        querySession,
        askQuestion,
        clearQuery,
        kpiDrilldown,
        openKpiDrilldown,
        closeKpiDrilldown,
      }}
    >
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  const ctx = useContext(SimulationContext);
  if (!ctx) throw new Error('useSimulation must be used within SimulationProvider');
  return ctx;
}
