import { useState } from 'react';
import { Box, Button, Grid } from '@mui/material';
import { GlassCard } from '../common/GlassCard';
import { ModuleHeader } from '../common/ModuleHeader';
import { IntakeTextField } from '../workflow/IntakeTextField';
import { IntakeSelectField } from '../workflow/IntakeSelectField';
import { GenerationSimulationPanel } from '../workflow/GenerationSimulationPanel';
import { GenerationRunHistoryPanel } from '../workflow/GenerationRunHistoryPanel';
import { ArtifactRepositoryPanel } from '../workflow/ArtifactRepositoryPanel';
import { useGenerationSimulation } from '../../hooks/useGenerationSimulation';
import type { SimulationConfig } from '../../hooks/useGenerationSimulation';
import {
  approvedRegressionOptions,
  buildReleaseArtifacts,
  createRunId,
  formatTimestamp,
  targetEnvironmentOptions,
  type ReleaseIntake,
} from '../../data/releaseArtifactFactory';
import type { Artifact, GenerationRun } from '../../types/artifacts';
import { colors } from '../../theme/colors';

const EMPTY_INTAKE: ReleaseIntake = {
  releaseVersion: '',
  targetEnvironment: '',
  regressionSuiteId: '',
};

const RELEASE_SIMULATION: SimulationConfig = {
  initialStatus: 'Release Agent reading approved test artifacts...',
  steps: [
    { progress: 25, activity: 'Reading Regression Suite', delayMs: 700 },
    { progress: 50, activity: 'Release Notes Generation', delayMs: 700 },
    { progress: 75, activity: 'Deployment Plan Generation', delayMs: 700 },
    { progress: 75, activity: 'Rollback Plan Generation', delayMs: 500 },
    { progress: 100, activity: 'Go-Live Checklist Generation', delayMs: 700 },
  ],
};

export function ReleaseIntakeWorkflow() {
  const [intake, setIntake] = useState<ReleaseIntake>(EMPTY_INTAKE);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [showSimulation, setShowSimulation] = useState(false);

  const { isRunning, progress, statusMessage, activityLog, run, reset } =
    useGenerationSimulation(RELEASE_SIMULATION);

  const updateField = (field: keyof ReleaseIntake, value: string) => {
    setIntake((prev) => ({ ...prev, [field]: value }));
  };

  const canGenerate =
    intake.releaseVersion.trim() !== '' &&
    intake.targetEnvironment !== '' &&
    intake.regressionSuiteId !== '';

  const handleGenerate = () => {
    if (!canGenerate) return;

    const runId = createRunId('REL');
    const timestamp = formatTimestamp();

    setShowSimulation(true);
    setRuns((prev) => [
      { runId, timestamp, generatedBy: 'Release AI', status: 'In Progress' },
      ...prev,
    ]);

    run(() => {
      setArtifacts(buildReleaseArtifacts(intake, runId));
      setRuns((prev) =>
        prev.map((r) => (r.runId === runId ? { ...r, status: 'Completed' } : r)),
      );
    });
  };

  const handleClear = () => {
    setIntake(EMPTY_INTAKE);
    reset();
    setShowSimulation(false);
  };

  return (
    <Box>
      <GlassCard sx={{ p: 2, mt: 1.5 }} glow="green">
        <ModuleHeader title="Release Intake" subtitle="Generate release artifacts from approved test deliverables" />
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, md: 4 }}>
            <IntakeTextField
              label="Release Version"
              value={intake.releaseVersion}
              onChange={(e) => updateField('releaseVersion', e.target.value)}
              placeholder="e.g. v2.4.1"
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <IntakeSelectField
              label="Target Environment"
              options={targetEnvironmentOptions}
              value={intake.targetEnvironment}
              onChange={(e) => updateField('targetEnvironment', e.target.value as string)}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <IntakeSelectField
              label="Approved Regression Suite"
              options={approvedRegressionOptions.map((o) => ({ value: o.id, label: o.label }))}
              value={intake.regressionSuiteId}
              onChange={(e) => updateField('regressionSuiteId', e.target.value as string)}
            />
          </Grid>
        </Grid>
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button
            variant="contained"
            disabled={isRunning || !canGenerate}
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
        agentLabel="Release Agent"
      />

      <GenerationRunHistoryPanel runs={runs} />

      <ArtifactRepositoryPanel
        artifacts={artifacts}
        title="Release Artifacts"
        subtitle="AI-generated release deliverables"
        emptyMessage="No release artifacts generated yet. Complete the intake form and click Generate Artifacts."
      />
    </Box>
  );
}
