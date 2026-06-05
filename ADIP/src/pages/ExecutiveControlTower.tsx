import { Box, Grid, Typography, Button, LinearProgress } from '@mui/material';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import { KpiCard } from '../components/common/KpiCard';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { DonutChart } from '../components/charts/DonutChart';
import { GaugeChart } from '../components/charts/GaugeChart';
import { HorizontalBarChart } from '../components/charts/HorizontalBarChart';
import { MultiLineChart } from '../components/charts/MultiLineChart';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function ExecutiveControlTower() {
  const { executive, release, governance, learning, dynamicInsights } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        {executive.kpis.map((kpi, i) => (
          <Grid key={kpi.label} size={{ xs: 6, md: 3 }}>
            <KpiCard label={kpi.label} value={kpi.value} trend={kpi.trend} data={kpi.data} delay={i * 0.05} />
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 6, md: 3 }}>
          <KpiCard label="Open Risks" value={executive.openRisks} suffix="" trend={executive.portfolioMetrics[3].trend} compact />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <KpiCard label="Open Incidents" value={executive.openIncidents} suffix="" trend={executive.portfolioMetrics[2].trend} compact />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <KpiCard label="Business Impact" value={executive.businessImpactScore} trend={1.2} compact />
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <KpiCard label="Portfolio Health" value={executive.portfolioHealth} trend={2.4} compact />
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        {executive.domainHealth.map((d, i) => (
          <Grid key={d.name} size={{ xs: 6, md: 4 }}>
            <GlassCard delay={0.1 + i * 0.05} sx={{ p: 1.5 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>{d.name}</Typography>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>{d.score}%</Typography>
                <Typography variant="caption" color="text.secondary">Health</Typography>
              </Box>
              <Box sx={{ height: 32, mt: 0.5 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={d.trend}>
                    <Area type="monotone" dataKey="value" stroke={colors.primary} fill={`${colors.primary}22`} strokeWidth={1.5} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                {[
                  { l: 'Changes', v: d.changes },
                  { l: 'Risks', v: d.risks },
                  { l: 'Incidents', v: d.incidents },
                ].map((m) => (
                  <Box key={m.l} sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem', display: 'block' }}>{m.l}</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 700, fontSize: '0.85rem' }}>{m.v}</Typography>
                  </Box>
                ))}
              </Box>
            </GlassCard>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 8 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader number={1} title="Domain Confidence Trend" subtitle="Net Banking · Mobile · Payments" />
            <MultiLineChart
              data={executive.confidenceTrend}
              series={[
                { key: 'net', color: colors.primary, name: 'Net Banking' },
                { key: 'mobile', color: colors.info, name: 'Mobile Banking' },
                { key: 'payments', color: colors.warning, name: 'Payments' },
              ]}
              height={220}
            />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2, height: '100%' }} glow="purple">
            <ModuleHeader title="Executive Insights" subtitle="Live · updates every 15s" />
            {dynamicInsights.map((insight) => (
              <Typography key={insight} variant="body2" color="text.secondary" sx={{ fontSize: '0.78rem', mb: 1, lineHeight: 1.5 }}>
                • {insight}
              </Typography>
            ))}
          </GlassCard>
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        {executive.portfolioMetrics.map((m, i) => (
          <Grid key={m.label} size={{ xs: 6, md: 3 }}>
            <KpiCard label={m.label} value={m.value} suffix="" trend={m.trend} delay={0.1 + i * 0.05} compact />
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Risk by SDLC Phase" />
            <DonutChart data={executive.riskByPhase} centerLabel="Open Risks" centerValue={executive.openRisks} height={150} />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }} glow="green">
            <ModuleHeader title="Release Confidence" />
            <GaugeChart value={release.confidence} label="Enterprise Avg" showGo />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Business Impact Areas" />
            <HorizontalBarChart data={executive.businessImpactAreas} height={150} barColor={colors.secondary} />
          </GlassCard>
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Critical Incidents" />
            {executive.criticalIncidents.map((inc) => (
              <Box key={inc.id} sx={{ p: 1, mb: 0.75, borderRadius: 1, bgcolor: colors.bg.glass, border: `1px solid ${colors.border.subtle}` }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>{inc.id}</Typography>
                  <SeverityChip severity={inc.severity} />
                </Box>
                <Typography variant="caption" sx={{ display: 'block', mt: 0.25 }}>{inc.title}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>{inc.domain} · {inc.duration}</Typography>
              </Box>
            ))}
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Enterprise Scorecard" />
            {executive.scorecard.map((s) => (
              <Box key={s.label} sx={{ mb: 1.25 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.25 }}>
                  <Typography variant="caption">{s.label}</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>{s.value}%</Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={s.value}
                  sx={{
                    height: 4,
                    borderRadius: 2,
                    bgcolor: 'rgba(255,255,255,0.06)',
                    '& .MuiLinearProgress-bar': { bgcolor: s.value >= 90 ? colors.success : colors.primary },
                  }}
                />
              </Box>
            ))}
            <ModuleHeader title="Governance Snapshot" />
            <DonutChart data={governance.findingSeverity} centerLabel="Findings" height={120} />
          </GlassCard>
        </Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Active AI Scans" />
        <Grid container spacing={1.5}>
          {executive.activeScans.map((scan) => (
            <Grid key={scan.name} size={{ xs: 12, md: 4 }}>
              <Box sx={{ p: 1.5, borderRadius: 1, border: `1px solid ${colors.border.subtle}` }}>
                <Typography variant="caption" sx={{ fontWeight: 600 }}>{scan.name}</Typography>
                <LinearProgress variant="determinate" value={scan.progress} sx={{ mt: 1, height: 4, borderRadius: 2 }} />
                <Typography variant="caption" color="text.secondary">{scan.status} · {scan.progress}%</Typography>
              </Box>
            </Grid>
          ))}
          <Grid size={{ xs: 12, md: 4 }}>
            <Typography variant="caption" color="text.secondary">
              Lessons learned: {learning.lessonsLearned} · Reusable assets: {learning.reusableAssets}
            </Typography>
            <Button size="small" sx={{ mt: 1, fontSize: '0.75rem' }}>View Learning Hub →</Button>
          </Grid>
        </Grid>
      </GlassCard>
    </Box>
  );
}
