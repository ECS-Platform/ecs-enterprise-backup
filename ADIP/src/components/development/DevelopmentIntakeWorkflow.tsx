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
  approvedHldOptions,
  approvedLldOptions,
  buildDevelopmentArtifacts,
  createRunId,
  formatTimestamp,
} from '../../data/developmentArtifactFactory';
import type { Artifact, GenerationRun } from '../../types/artifacts';
import { colors } from '../../theme/colors';

const DEVELOPMENT_SIMULATION: SimulationConfig = {
  initialStatus: 'Development Agent reading approved design artifacts...',
  steps: [
    { progress: 25, activity: 'Reading HLD & LLD', delayMs: 700 },
    { progress: 50, activity: 'API Specification Generation', delayMs: 700 },
    { progress: 75, activity: 'Service Design Generation', delayMs: 700 },
    { progress: 75, activity: 'Database Script Generation', delayMs: 500 },
    { progress: 100, activity: 'Code Package Scaffolding', delayMs: 700 },
  ],
};

export function DevelopmentIntakeWorkflow() {
  const [approvedHld, setApprovedHld] = useState('');
  const [approvedLld, setApprovedLld] = useState('');
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [showSimulation, setShowSimulation] = useState(false);

  const { isRunning, progress, statusMessage, activityLog, run, reset } =
    useGenerationSimulation(DEVELOPMENT_SIMULATION);

  const handleGenerate = () => {
    if (!approvedHld || !approvedLld) return;

    const runId = createRunId('DEV');
    const timestamp = formatTimestamp();

    setShowSimulation(true);
    setRuns((prev) => [
      { runId, timestamp, generatedBy: 'Development AI', status: 'In Progress' },
      ...prev,
    ]);

    run(() => {
      setArtifacts(buildDevelopmentArtifacts(approvedHld, approvedLld, runId));
      setRuns((prev) =>
        prev.map((r) => (r.runId === runId ? { ...r, status: 'Completed' } : r)),
      );
    });
  };

  const handleClear = () => {
    setApprovedHld('');
    setApprovedLld('');
    reset();
    setShowSimulation(false);
  };

  return (
    <Box>
      <GlassCard sx={{ p: 2, mt: 1.5 }} glow="purple">
        <ModuleHeader title="Development Intake" subtitle="Generate development artifacts from approved design" />
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, md: 6 }}>
            <IntakeSelectField
              label="Approved HLD"
              options={approvedHldOptions.map((o) => ({ value: o.id, label: o.label }))}
              value={approvedHld}
              onChange={(e) => setApprovedHld(e.target.value as string)}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <IntakeSelectField
              label="Approved LLD"
              options={approvedLldOptions.map((o) => ({ value: o.id, label: o.label }))}
              value={approvedLld}
              onChange={(e) => setApprovedLld(e.target.value as string)}
            />
          </Grid>
        </Grid>
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button
            variant="contained"
            disabled={isRunning || !approvedHld || !approvedLld}
            onClick={handleGenerate}
            sx={{ minWidth: 180, bgcolor: colors.secondary }}
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
        agentLabel="Development Agent"
      />

      <GenerationRunHistoryPanel runs={runs} />

      <ArtifactRepositoryPanel
        artifacts={artifacts}
        title="Development Artifacts"
        subtitle="AI-generated development deliverables"
        emptyMessage="No development artifacts generated yet. Select approved HLD and LLD, then click Generate Artifacts."
      />
    </Box>
  );
}
