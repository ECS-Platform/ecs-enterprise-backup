import { Box, Grid, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, CartesianGrid, Tooltip } from 'recharts';
import { KpiCard } from '../components/common/KpiCard';
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
            <Box sx={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={production.incidentTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.border.subtle} vertical={false} />
                  <XAxis dataKey="day" tick={{ fill: colors.text.muted, fontSize: 11 }} />
                  <YAxis tick={{ fill: colors.text.muted, fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: colors.bg.secondary, borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="count" fill={colors.critical} barSize={32} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Service Health" />
            {production.serviceHealth.map((s) => (
              <Box key={s.name} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}>
                <StatusDot status={s.status} />
                <Typography variant="caption" sx={{ flex: 1 }}>{s.name}</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>{s.uptime}%</Typography>
              </Box>
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
              <Box key={inc.id} sx={{ p: 1, mb: 0.75, borderRadius: 1, border: `1px solid ${colors.border.subtle}` }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>{inc.id}</Typography>
                  <SeverityChip severity={inc.severity} />
                </Box>
                <Typography variant="caption">{inc.title}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', display: 'block' }}>{inc.domain} · {inc.status}</Typography>
              </Box>
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
