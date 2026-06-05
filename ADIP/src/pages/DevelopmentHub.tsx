import { Box, Grid, Typography } from '@mui/material';
import { KpiCard } from '../components/common/KpiCard';
import { DrilldownTableRow } from '../components/common/DrilldownTableRow';
import { BarChartPanel } from '../components/charts/BarChartPanel';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { MultiLineChart } from '../components/charts/MultiLineChart';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function DevelopmentHub() {
  const { development } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Pull Requests" value={development.pullRequests} suffix="" trend={8} compact /></Grid>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Commits" value={development.commits} suffix="" trend={5} compact /></Grid>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Code Quality" value={development.codeQuality} trend={1.2} compact /></Grid>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Tech Debt" value={development.techDebt} suffix="" trend={-3} compact /></Grid>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Dev Health" value={development.health} trend={2} compact /></Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 7 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Quality vs Technical Debt" />
            <MultiLineChart
              data={development.qualityTrend}
              series={[
                { key: 'quality', color: colors.success, name: 'Code Quality' },
                { key: 'debt', color: colors.warning, name: 'Tech Debt Index' },
              ]}
              height={220}
            />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="PR Aging Distribution" />
            <BarChartPanel
              chartId="development.pr-aging"
              data={development.prAging}
              categoryKey="range"
              series={[{ dataKey: 'count', name: 'PRs', fill: colors.secondary, barSize: 28, radius: [4, 4, 0, 0] }]}
              height={220}
            />
          </GlassCard>
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 8 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Weekly Commit & PR Volume" />
            <BarChartPanel
              chartId="development.commit-trend"
              data={development.commitTrend}
              categoryKey="week"
              series={[
                { dataKey: 'commits', name: 'Commits', fill: colors.primary, barSize: 22 },
                { dataKey: 'prs', name: 'PRs', fill: colors.info, barSize: 22 },
              ]}
              height={200}
              showLegend
            />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Security Findings" subtitle={`${development.securityFindings} open`} />
            {development.securityItems.map((f) => (
              <DrilldownTableRow
                key={f.title}
                chartId="development.security-items"
                segment={f.title}
                label={f.title}
                value={f.severity}
                sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}
              >
                <Typography variant="caption" sx={{ fontSize: '0.72rem', flex: 1, mr: 1 }}>{f.title}</Typography>
                <SeverityChip severity={f.severity} />
              </DrilldownTableRow>
            ))}
          </GlassCard>
        </Grid>
      </Grid>
    </Box>
  );
}
