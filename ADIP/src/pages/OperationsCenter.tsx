import { Box, Grid, Typography } from '@mui/material';
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, ResponsiveContainer, CartesianGrid, Tooltip, Legend } from 'recharts';
import { KpiCard } from '../components/common/KpiCard';
import { DrilldownTableRow } from '../components/common/DrilldownTableRow';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { GaugeChart } from '../components/charts/GaugeChart';
import { AIInsightBox } from '../components/common/AIInsightBox';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function OperationsCenter() {
  const { operations } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Batch Health" value={operations.batchHealth} trend={1} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Capacity Utilization" value={operations.capacityUtilization} trend={3} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="CPU Utilization" value={operations.cpuUtilization} suffix="%" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Storage Utilization" value={operations.storageUtilization} suffix="%" /></Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 8 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Capacity Trend (24h)" subtitle="CPU · Memory · Storage" />
            <Box sx={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={operations.capacityTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.border.subtle} vertical={false} />
                  <XAxis dataKey="hour" tick={{ fill: colors.text.muted, fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: colors.text.muted, fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: colors.bg.secondary, borderRadius: 8, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area type="monotone" dataKey="cpu" name="CPU" stroke={colors.primary} fill={`${colors.primary}22`} strokeWidth={2} />
                  <Area type="monotone" dataKey="memory" name="Memory" stroke={colors.secondary} fill={`${colors.secondary}22`} strokeWidth={2} />
                  <Area type="monotone" dataKey="storage" name="Storage" stroke={colors.warning} fill={`${colors.warning}22`} strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </Box>
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2, textAlign: 'center' }}>
            <ModuleHeader title="Operational Health" />
            <GaugeChart chartId="operations.health-gauge" value={operations.operationalHealth} label="Health Score" size={180} />
          </GlassCard>
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Capacity Forecast" />
            <Box sx={{ height: 160 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={operations.capacityForecast}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.border.subtle} />
                  <XAxis dataKey="day" tick={{ fill: colors.text.muted, fontSize: 11 }} />
                  <YAxis domain={[60, 90]} tick={{ fill: colors.text.muted, fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: colors.bg.secondary, borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="predicted" stroke={colors.warning} strokeWidth={2} dot name="Predicted %" />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Batch Monitoring" subtitle={`${operations.activeJobs} active · ${operations.failedJobs} failed`} />
            {operations.batchJobs.map((job) => (
              <DrilldownTableRow
                key={job.name}
                chartId="operations.batch-jobs"
                segment={job.name}
                label={job.name}
                value={job.progress}
                suffix="%"
                sx={{ display: 'flex', gap: 2, py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}
              >
                <Typography variant="caption" sx={{ flex: 1 }}>{job.name}</Typography>
                <Typography variant="caption" sx={{ color: job.status === 'Failed' ? colors.critical : colors.success }}>{job.status}</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700 }}>{job.progress}%</Typography>
              </DrilldownTableRow>
            ))}
          </GlassCard>
        </Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Operational Risks" />
        {operations.operationalRisks.map((r) => (
          <Box key={r.title} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}>
            <Typography variant="caption">{r.title}</Typography>
            <SeverityChip severity={r.severity} />
          </Box>
        ))}
        <AIInsightBox insight="Settlement DB pool nearing threshold before EOD UPI batch — scale recommended." />
      </GlassCard>
    </Box>
  );
}
