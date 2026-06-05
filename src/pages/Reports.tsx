import { Box, Grid, Typography } from '@mui/material';
import { KpiCard } from '../components/common/KpiCard';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';
import { colors } from '../theme/colors';

export function Reports() {
  const { reports, executive } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 4 }}><KpiCard label="Reports Generated" value={reports.generated} suffix="" trend={4} /></Grid>
        <Grid size={{ xs: 6, md: 4 }}><KpiCard label="Scheduled Reports" value={reports.scheduled} suffix="" /></Grid>
        <Grid size={{ xs: 6, md: 4 }}><KpiCard label="Portfolio Health" value={executive.portfolioHealth} trend={2} /></Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Operations Report Catalog" subtitle={`Last export: ${reports.lastExport}`} />
        {reports.reportTypes.map((r) => (
          <Box key={r.name} sx={{ display: 'flex', gap: 2, py: 1.25, borderBottom: `1px solid ${colors.border.subtle}`, cursor: 'pointer', '&:hover': { bgcolor: colors.bg.glass } }}>
            <Typography variant="caption" sx={{ flex: 1, fontWeight: 600, fontSize: '0.8125rem' }}>{r.name}</Typography>
            <Typography variant="caption" sx={{ color: colors.primary, fontWeight: 700 }}>{r.type}</Typography>
          </Box>
        ))}
      </GlassCard>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Suggested Operations Reports" />
        {[
          'Daily UPI Settlement Control Pack',
          'Fraud Engine Incident Summary',
          'Batch Job Failure Analysis',
          'Cross-Domain Release Readiness',
        ].map((name) => (
          <Typography key={name} variant="caption" sx={{ display: 'block', py: 0.75, color: colors.text.secondary }}>
            • {name}
          </Typography>
        ))}
      </GlassCard>
    </Box>
  );
}
