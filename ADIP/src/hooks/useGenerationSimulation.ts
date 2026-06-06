import { useCallback, useRef, useState } from 'react';

export interface SimulationStep {
  progress: number;
  activity: string;
  delayMs: number;
}

export interface SimulationConfig {
  initialStatus: string;
  steps: SimulationStep[];
}

export function useGenerationSimulation(config: SimulationConfig) {
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [activityLog, setActivityLog] = useState<string[]>([]);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const reset = useCallback(() => {
    clearTimers();
    setIsRunning(false);
    setProgress(0);
    setStatusMessage('');
    setActivityLog([]);
  }, [clearTimers]);

  const run = useCallback(
    (onComplete?: () => void) => {
      clearTimers();
      setIsRunning(true);
      setProgress(0);
      setActivityLog([]);
      setStatusMessage(config.initialStatus);

      let cumulativeDelay = 600;

      config.steps.forEach((step) => {
        const progressTimer = setTimeout(() => {
          setProgress(step.progress);
        }, cumulativeDelay);
        timersRef.current.push(progressTimer);

        cumulativeDelay += step.delayMs;

        const activityTimer = setTimeout(() => {
          setActivityLog((prev) => [...prev, step.activity]);
        }, cumulativeDelay);
        timersRef.current.push(activityTimer);

        cumulativeDelay += 200;
      });

      const completeTimer = setTimeout(() => {
        setIsRunning(false);
        setStatusMessage('Generation complete');
        onComplete?.();
      }, cumulativeDelay + 400);
      timersRef.current.push(completeTimer);
    },
    [clearTimers, config],
  );

  return { isRunning, progress, statusMessage, activityLog, run, reset };
}
