import { Box, Grid, Typography, Button } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { KpiCard } from '../components/common/KpiCard';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { GaugeChart } from '../components/charts/GaugeChart';
import { CircularGauge } from '../components/charts/CircularGauge';
import { StatusDot } from '../components/common/StatusDot';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function ReleaseCenter() {
  const { release } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Release Confidence" value={release.confidence} trend={2} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Rollback Readiness" value={release.rollbackReadiness} trend={1} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Deployment Readiness" value={release.deploymentReadiness} trend={-1} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Go / No-Go" value={release.goNoGo} suffix="" /></Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2, textAlign: 'center' }} glow="green">
            <ModuleHeader title="Enterprise Release Confidence" />
            <GaugeChart value={release.confidence} label="Confidence Score" showGo size={220} />
            <Button variant="contained" sx={{ mt: 1, bgcolor: colors.success }}>Run Readiness Assessment</Button>
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Readiness by Dimension" />
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'center' }}>
              {release.readiness.map((r) => (
                <CircularGauge key={r.dimension} value={r.score} label={r.dimension} />
              ))}
            </Box>
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Assessment Checklist" />
            {release.checklist.map((c) => (
              <Box key={c.item} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}>
                {c.status === 'completed' ? <CheckCircleIcon sx={{ fontSize: 16, color: colors.success }} /> : <StatusDot status={c.status} />}
                <Typography variant="caption" sx={{ flex: 1 }}>{c.item}</Typography>
              </Box>
            ))}
          </GlassCard>
        </Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="In-Flight Banking Releases" />
        {release.releases.map((r) => (
          <Box key={r.id} sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 1, borderBottom: `1px solid ${colors.border.subtle}` }}>
            <Typography variant="caption" sx={{ fontWeight: 700, minWidth: 100 }}>{r.id}</Typography>
            <Typography variant="caption" sx={{ flex: 1 }}>{r.name}</Typography>
            <Typography variant="caption" color="text.secondary">{r.domain}</Typography>
            <Typography variant="caption" sx={{ fontWeight: 700, color: r.confidence >= 90 ? colors.success : colors.warning }}>{r.confidence}%</Typography>
            <SeverityChip severity={r.risk} />
          </Box>
        ))}
      </GlassCard>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Release Risk Matrix" />
        {release.riskMatrix.map((r) => (
          <Box key={r.title} sx={{ display: 'flex', gap: 2, py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}>
            <Typography variant="caption" sx={{ flex: 1 }}>{r.title}</Typography>
            <Typography variant="caption" color="text.secondary">{r.domain}</Typography>
            <SeverityChip severity={r.severity} />
          </Box>
        ))}
      </GlassCard>
    </Box>
  );
}
