import { Box, Grid, Typography } from '@mui/material';
import { KpiCard } from '../components/common/KpiCard';
import { DrilldownTableRow } from '../components/common/DrilldownTableRow';
import { BarChartPanel } from '../components/charts/BarChartPanel';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function DeliveryHub() {
  const { delivery } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Requirements Analysed" value={delivery.requirementsAnalysed} suffix="" trend={4} delay={0} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Business Impact Index" value={delivery.businessImpactIndex} trend={1.8} delay={0.05} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Compliance Impact" value={delivery.complianceImpactCount} suffix=" reqs" delay={0.1} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Requirement Risks" value={delivery.requirementRisks} suffix="" trend={-2} delay={0.15} /></Grid>
      </Grid>
      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Architecture Risks" value={delivery.architectureRisks} suffix="" delay={0.2} compact /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Technical Debt" value={delivery.technicalDebtItems} suffix=" items" delay={0.25} compact /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Test Coverage" value={delivery.testCoverageAvg} trend={0.8} delay={0.3} compact /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Code Quality" value={delivery.codeQualityAvg} trend={1.1} delay={0.35} compact /></Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="SDLC Pipeline Velocity" subtitle="Items per stage" />
            <BarChartPanel
              chartId="delivery.pipeline-velocity"
              data={delivery.pipelineVelocity}
              categoryKey="stage"
              series={[{ dataKey: 'count', name: 'Items', fill: colors.primary, barSize: 16, radius: [0, 4, 4, 0] }]}
              height={200}
              layout="vertical"
            />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Sprint Burndown" subtitle="Planned vs actual" />
            <BarChartPanel
              chartId="delivery.sprint-burndown"
              data={delivery.sprintBurndown}
              categoryKey="day"
              series={[
                { dataKey: 'planned', name: 'Planned', fill: colors.text.muted, barSize: 20 },
                { dataKey: 'actual', name: 'Actual', fill: colors.success, barSize: 20 },
              ]}
              height={200}
              showLegend
            />
          </GlassCard>
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Change Failure Rate" value={delivery.changeFailureRate} suffix="%" compact /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Deployments / Month" value={delivery.deploymentFrequency} suffix="" compact /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Lead Time" value={delivery.leadTimeHours} suffix=" hrs" compact /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Defect Density" value={delivery.defectDensity} suffix="/KLOC" compact /></Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Active Banking Requirements" />
        {delivery.topRequirements.map((req) => (
          <DrilldownTableRow
            key={req.id}
            chartId="delivery.top-requirements"
            segment={req.id}
            label={req.title}
            value={req.id}
            sx={{ display: 'flex', gap: 2, py: 1, borderBottom: `1px solid ${colors.border.subtle}` }}
          >
            <Typography variant="caption" sx={{ fontWeight: 700, minWidth: 100 }}>{req.id}</Typography>
            <Typography variant="caption" sx={{ flex: 1 }}>{req.title}</Typography>
            <Typography variant="caption" color="text.secondary">{req.domain}</Typography>
            <SeverityChip severity={req.risk} />
          </DrilldownTableRow>
        ))}
      </GlassCard>
    </Box>
  );
}
