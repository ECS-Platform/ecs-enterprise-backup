import { Box, Grid, Typography } from '@mui/material';
import { KpiCard } from '../components/common/KpiCard';
import { DrilldownTableRow } from '../components/common/DrilldownTableRow';
import { BarChartPanel } from '../components/charts/BarChartPanel';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { StatusDot } from '../components/common/StatusDot';
import { AIInsightBox } from '../components/common/AIInsightBox';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function ProductionCenter() {
  const { production } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Availability" value={production.availability} trend={0.01} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="MTTR" value={`${production.mttrMinutes}m`} suffix="" trend={-5} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Service Health" value={production.health} trend={1} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Open Incidents" value={production.activeIncidents} suffix="" trend={-12} /></Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 7 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Incident Trend (7 days)" />
            <BarChartPanel
              chartId="production.incident-trend"
              data={production.incidentTrend}
              categoryKey="day"
              series={[{ dataKey: 'count', name: 'Incidents', fill: colors.critical, barSize: 32, radius: [4, 4, 0, 0] }]}
              height={200}
            />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Service Health" />
            {production.serviceHealth.map((s) => (
              <DrilldownTableRow
                key={s.name}
                chartId="production.service-health"
                segment={s.name}
                label={s.name}
                value={s.uptime}
                suffix="%"
                sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}
              >
                <StatusDot status={s.status} />
                <Typography variant="caption" sx={{ flex: 1 }}>{s.name}</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>{s.uptime}%</Typography>
              </DrilldownTableRow>
            ))}
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>SLA breaches (24h): {production.slaBreaches}</Typography>
          </GlassCard>
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Open Incidents" />
            {production.openIncidents.map((inc) => (
              <DrilldownTableRow
                key={inc.id}
                chartId="production.open-incidents"
                segment={inc.id}
                label={inc.title}
                value={inc.id}
                sx={{ p: 1, mb: 0.75, borderRadius: 1, border: `1px solid ${colors.border.subtle}` }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>{inc.id}</Typography>
                  <SeverityChip severity={inc.severity} />
                </Box>
                <Typography variant="caption">{inc.title}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', display: 'block' }}>{inc.domain} · {inc.status}</Typography>
              </DrilldownTableRow>
            ))}
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Top Issues & RCA" />
            {production.topIssues.map((item) => (
              <Box key={item.issue} sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ fontWeight: 700, display: 'block' }}>{item.issue}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.72rem', lineHeight: 1.5 }}>{item.rca}</Typography>
              </Box>
            ))}
            <AIInsightBox insight="Fraud Engine and UPI Switch require operations war-room until peak window ends." />
          </GlassCard>
        </Grid>
      </Grid>
    </Box>
  );
}
