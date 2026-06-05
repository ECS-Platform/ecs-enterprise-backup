import { Box, Grid, Typography } from '@mui/material';
import { KpiCard } from '../components/common/KpiCard';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { DependencyGraph } from '../components/charts/DependencyGraph';
import { CircularGauge } from '../components/charts/CircularGauge';
import { AIInsightBox } from '../components/common/AIInsightBox';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function ArchitectureHub() {
  const { architecture } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Architecture Readiness" value={architecture.readiness} trend={1.5} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Critical Dependencies" value={architecture.criticalDependencies} suffix="" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Integration Risks" value={architecture.integrationRisks} suffix="" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Cross-Team Dependencies" value={architecture.crossTeamDeps} suffix="" /></Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 8 }}>
          <GlassCard sx={{ p: 2 }} glow="blue">
            <ModuleHeader number={3} title="UPI & Payments Dependency Map" />
            <DependencyGraph nodes={architecture.services} edges={architecture.edges} height={280} />
            <AIInsightBox title="AI Architecture Insight" insight={architecture.recommendations[0]} />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Layer Readiness" />
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'center', mt: 1 }}>
              {architecture.layerReadiness.map((g) => (
                <CircularGauge key={g.label} chartId="architecture.layer-readiness" value={g.value} label={g.label} />
              ))}
            </Box>
          </GlassCard>
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Technology Risks" />
            {architecture.techRisks.map((r) => (
              <Box key={r.title} sx={{ display: 'flex', justifyContent: 'space-between', py: 1, borderBottom: `1px solid ${colors.border.subtle}` }}>
                <Typography variant="caption">{r.title}</Typography>
                <SeverityChip severity={r.severity} />
              </Box>
            ))}
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Architecture Recommendations" />
            {architecture.recommendations.map((rec, i) => (
              <Typography key={rec} variant="caption" sx={{ display: 'block', mb: 1, fontSize: '0.78rem', color: colors.text.secondary }}>
                {i + 1}. {rec}
              </Typography>
            ))}
          </GlassCard>
        </Grid>
      </Grid>
    </Box>
  );
}
