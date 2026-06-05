/**
 * Backwards-compatibility shim.
 *
 * The simulation logic now lives in `simulationEngine.js`. This module exists
 * solely so that any caller still importing from `services/simulationService`
 * keeps working without behavioural change. New code should import directly
 * from `./simulationEngine.js`.
 */

export {
  getRefreshInterval,
  tickSimulation,
  startSimulation,
  stopSimulation,
  forceTick,
  generateExecutiveInsights,
} from './simulationEngine.js';
