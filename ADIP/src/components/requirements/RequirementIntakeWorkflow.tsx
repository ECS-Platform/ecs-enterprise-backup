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
  buildRequirementArtifacts,
  createRunId,
  formatTimestamp,
  type RequirementIntake,
} from '../../data/requirementArtifactFactory';
import type { Artifact, GenerationRun } from '../../types/artifacts';
import { DOMAINS } from '../../services/mockDataEngine.js';
import { colors } from '../../theme/colors';

const EMPTY_INTAKE: RequirementIntake = {
  domain: '',
  featureName: '',
  businessObjective: '',
  requirementDescription: '',
  complianceNotes: '',
};

const REQUIREMENT_SIMULATION: SimulationConfig = {
  initialStatus: 'Requirement Agent reading business input...',
  steps: [
    { progress: 25, activity: 'Requirement Analysis', delayMs: 700 },
    { progress: 50, activity: 'BRD Generation', delayMs: 700 },
    { progress: 75, activity: 'FRD Generation', delayMs: 700 },
    { progress: 75, activity: 'User Story Generation', delayMs: 500 },
    { progress: 100, activity: 'Acceptance Criteria Generation', delayMs: 700 },
  ],
};

const domainOptions = DOMAINS.filter((d) => d.id !== 'all').map((d) => ({
  value: d.label,
  label: d.label,
}));

export function RequirementIntakeWorkflow() {
  const [intake, setIntake] = useState<RequirementIntake>(EMPTY_INTAKE);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [runs, setRuns] = useState<GenerationRun[]>([]);
  const [showSimulation, setShowSimulation] = useState(false);

  const { isRunning, progress, statusMessage, activityLog, run, reset } =
    useGenerationSimulation(REQUIREMENT_SIMULATION);

  const updateField = (field: keyof RequirementIntake, value: string) => {
    setIntake((prev) => ({ ...prev, [field]: value }));
  };

  const handleGenerate = () => {
    const runId = createRunId('REQ');
    const timestamp = formatTimestamp();

    setShowSimulation(true);
    setRuns((prev) => [
      { runId, timestamp, generatedBy: 'Requirement AI', status: 'In Progress' },
      ...prev,
    ]);

    run(() => {
      setArtifacts(buildRequirementArtifacts(intake, runId));
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
      <GlassCard sx={{ p: 2, mt: 1.5 }} glow="purple">
        <ModuleHeader title="Requirement Intake" subtitle="Capture business input for AI artifact generation" />
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, md: 6 }}>
            <IntakeSelectField
              label="Domain"
              options={domainOptions}
              value={intake.domain}
              onChange={(e) => updateField('domain', e.target.value as string)}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <IntakeTextField
              label="Feature Name"
              value={intake.featureName}
              onChange={(e) => updateField('featureName', e.target.value)}
              placeholder="e.g. UPI Limit Enhancement"
            />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <IntakeTextField
              label="Business Objective"
              value={intake.businessObjective}
              onChange={(e) => updateField('businessObjective', e.target.value)}
              multiline
              rows={2}
              placeholder="Describe the business goal and expected outcome"
            />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <IntakeTextField
              label="Requirement Description"
              value={intake.requirementDescription}
              onChange={(e) => updateField('requirementDescription', e.target.value)}
              multiline
              rows={3}
              placeholder="Detailed functional and non-functional requirements"
            />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <IntakeTextField
              label="Compliance Notes"
              value={intake.complianceNotes}
              onChange={(e) => updateField('complianceNotes', e.target.value)}
              multiline
              rows={2}
              placeholder="RBI, PCI-DSS, or internal policy constraints"
            />
          </Grid>
        </Grid>
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button
            variant="contained"
            disabled={isRunning}
            onClick={handleGenerate}
            sx={{ minWidth: 160, bgcolor: colors.secondary }}
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
        agentLabel="Requirement Agent"
      />

      <GenerationRunHistoryPanel runs={runs} />

      <ArtifactRepositoryPanel
        artifacts={artifacts}
        title="Generated Artifacts"
        subtitle="AI-generated requirement deliverables"
        emptyMessage="No artifacts generated yet. Complete the intake form and click Generate Artifacts."
      />
    </Box>
  );
}
