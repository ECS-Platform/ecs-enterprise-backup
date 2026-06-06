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
  approvedBrdOptions,
  approvedFrdOptions,
  buildDesignArtifacts,
  createRunId,
  formatTimestamp,
} from '../../data/designArtifactFactory';
import type { Artifact, GenerationRun } from '../../types/artifacts';
import { colors } from '../../theme/colors';

const DESIGN_SIMULATION: SimulationConfig = {
  initialStatus: 'Design Agent reading approved requirements...',
  steps: [
    { progress: 25, activity: 'Reading BRD', delayMs: 700 },
    { progress: 50, activity: 'Building HLD', delayMs: 700 },
    { progress: 75, activity: 'Building LLD', delayMs: 700 },
    { progress: 75, activity: 'Generating APIs', delayMs: 500 },
    { progress: 100, activity: 'Generating Data Model', delayMs: 700 },
  ],
};

export function DesignIntakeWorkflow() {
  const [approvedBrd, setApprovedBrd] = useState('');
  const [approvedFrd, setApprovedFrd] = useState('');
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [showSimulation, setShowSimulation] = useState(false);

  const { isRunning, progress, statusMessage, activityLog, run, reset } =
    useGenerationSimulation(DESIGN_SIMULATION);

  const handleGenerate = () => {
    if (!approvedBrd || !approvedFrd) return;

    const runId = createRunId('ARCH');
    const timestamp = formatTimestamp();

    setShowSimulation(true);
    setRuns((prev) => [
      { runId, timestamp, generatedBy: 'Design AI', status: 'In Progress' },
      ...prev,
    ]);

    run(() => {
      setArtifacts(buildDesignArtifacts(approvedBrd, approvedFrd, runId));
      setRuns((prev) =>
        prev.map((r) => (r.runId === runId ? { ...r, status: 'Completed' } : r)),
      );
    });
  };

  const handleClear = () => {
    setApprovedBrd('');
    setApprovedFrd('');
    reset();
    setShowSimulation(false);
  };

  return (
    <Box>
      <GlassCard sx={{ p: 2, mt: 1.5 }} glow="blue">
        <ModuleHeader title="Design Intake" subtitle="Generate architecture artifacts from approved requirements" />
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, md: 6 }}>
            <IntakeSelectField
              label="Approved BRD"
              options={approvedBrdOptions.map((o) => ({ value: o.id, label: o.label }))}
              value={approvedBrd}
              onChange={(e) => setApprovedBrd(e.target.value as string)}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <IntakeSelectField
              label="Approved FRD"
              options={approvedFrdOptions.map((o) => ({ value: o.id, label: o.label }))}
              value={approvedFrd}
              onChange={(e) => setApprovedFrd(e.target.value as string)}
            />
          </Grid>
        </Grid>
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button
            variant="contained"
            disabled={isRunning || !approvedBrd || !approvedFrd}
            onClick={handleGenerate}
            sx={{ minWidth: 180, bgcolor: colors.primary }}
          >
            Generate Design Artifacts
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
        agentLabel="Design Agent"
      />

      <GenerationRunHistoryPanel runs={runs} />

      <ArtifactRepositoryPanel
        artifacts={artifacts}
        title="Design Artifacts"
        subtitle="AI-generated architecture deliverables"
        emptyMessage="No design artifacts generated yet. Select approved BRD and FRD, then click Generate Design Artifacts."
      />
    </Box>
  );
}
