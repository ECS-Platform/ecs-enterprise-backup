import { useState } from 'react';
import { Box, Button, Grid } from '@mui/material';
import { GlassCard } from '../common/GlassCard';
import { ModuleHeader } from '../common/ModuleHeader';
import { IntakeSelectField } from '../workflow/IntakeSelectField';
import { GenerationSimulationPanel } from '../workflow/GenerationSimulationPanel';
import { GenerationRunHistoryPanel } from '../workflow/GenerationRunHistoryPanel';
import { ArtifactRepositoryPanel } from '../workflow/ArtifactRepositoryPanel';
import { useGenerationSimulation } from '../../hooks/useGenerationSimulation';
import type { SimulationConfig } from '../../hooks/useGenerationSimulation';
import {
  approvedApiSpecOptions,
  approvedServiceDesignOptions,
  buildTestingArtifacts,
  createRunId,
  formatTimestamp,
} from '../../data/testingArtifactFactory';
import type { Artifact, GenerationRun } from '../../types/artifacts';
import { colors } from '../../theme/colors';

const TESTING_SIMULATION: SimulationConfig = {
  initialStatus: 'Testing Agent reading approved development artifacts...',
  steps: [
    { progress: 25, activity: 'Reading API Specification', delayMs: 700 },
    { progress: 50, activity: 'Test Scenario Generation', delayMs: 700 },
    { progress: 75, activity: 'Test Case Generation', delayMs: 700 },
    { progress: 75, activity: 'Regression Suite Assembly', delayMs: 500 },
    { progress: 100, activity: 'Coverage Report Generation', delayMs: 700 },
  ],
};

export function TestingIntakeWorkflow() {
  const [approvedApi, setApprovedApi] = useState('');
  const [approvedService, setApprovedService] = useState('');
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [showSimulation, setShowSimulation] = useState(false);

  const { isRunning, progress, statusMessage, activityLog, run, reset } =
    useGenerationSimulation(TESTING_SIMULATION);

  const handleGenerate = () => {
    if (!approvedApi || !approvedService) return;

    const runId = createRunId('TEST');
    const timestamp = formatTimestamp();

    setShowSimulation(true);
    setRuns((prev) => [
      { runId, timestamp, generatedBy: 'Testing AI', status: 'In Progress' },
      ...prev,
    ]);

    run(() => {
      setArtifacts(buildTestingArtifacts(approvedApi, approvedService, runId));
      setRuns((prev) =>
        prev.map((r) => (r.runId === runId ? { ...r, status: 'Completed' } : r)),
      );
    });
  };

  const handleClear = () => {
    setApprovedApi('');
    setApprovedService('');
    reset();
    setShowSimulation(false);
  };

  return (
    <Box>
      <GlassCard sx={{ p: 2, mt: 1.5 }} glow="green">
        <ModuleHeader title="Testing Intake" subtitle="Generate test artifacts from approved development deliverables" />
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, md: 6 }}>
            <IntakeSelectField
              label="Approved API Specification"
              options={approvedApiSpecOptions.map((o) => ({ value: o.id, label: o.label }))}
              value={approvedApi}
              onChange={(e) => setApprovedApi(e.target.value as string)}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <IntakeSelectField
              label="Approved Service Design"
              options={approvedServiceDesignOptions.map((o) => ({ value: o.id, label: o.label }))}
              value={approvedService}
              onChange={(e) => setApprovedService(e.target.value as string)}
            />
          </Grid>
        </Grid>
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button
            variant="contained"
            disabled={isRunning || !approvedApi || !approvedService}
            onClick={handleGenerate}
            sx={{ minWidth: 180, bgcolor: colors.success }}
          >
            Generate Artifacts
          </Button>
          <Button variant="outlined" disabled={isRunning} onClick={handleClear}>
            Clear
          </Button>
        </Box>
      </GlassCard>

      <GenerationSimulationPanel
        visible={showSimulation}
        statusMessage={statusMessage}
        progress={progress}
        activityLog={activityLog}
        agentLabel="Testing Agent"
      />

      <GenerationRunHistoryPanel runs={runs} />

      <ArtifactRepositoryPanel
        artifacts={artifacts}
        title="Testing Artifacts"
        subtitle="AI-generated test deliverables"
        emptyMessage="No testing artifacts generated yet. Select approved API and service design, then click Generate Artifacts."
      />
    </Box>
  );
}
