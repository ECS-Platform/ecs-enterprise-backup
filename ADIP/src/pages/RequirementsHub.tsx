import { Box, Grid, Typography, Button, TextField } from '@mui/material';
import { KpiCard } from '../components/common/KpiCard';
import { DrilldownTableRow } from '../components/common/DrilldownTableRow';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { GaugeChart } from '../components/charts/GaugeChart';
import { DonutChart } from '../components/charts/DonutChart';
import { HorizontalBarChart } from '../components/charts/HorizontalBarChart';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';
import { colors } from '../theme/colors';

export function RequirementsHub() {
  const { requirements } = useFilteredSimulation();

  return (
    <Box>
      <GlassCard sx={{ p: 2, mb: 1.5 }} glow="purple">
        <ModuleHeader number={2} title="Requirement Analysis" subtitle="Banking requirements queue" />
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <TextField fullWidth multiline rows={2} placeholder="e.g. UPI Limit Enhancement, Merchant Auto Settlement..." size="small" sx={{ '& .MuiOutlinedInput-root': { bgcolor: colors.bg.glass, fontSize: '0.8125rem' } }} />
          <Button variant="contained" sx={{ minWidth: 140, bgcolor: colors.secondary, alignSelf: 'flex-start' }}>Analyze with AI</Button>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>{requirements.analysisQueue} items in analysis queue</Typography>
      </GlassCard>

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Requirements Analysed" value={requirements.analysed} suffix="" trend={6} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="High Risk" value={requirements.highRisk} suffix="" trend={-1} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Ambiguous" value={requirements.ambiguous} suffix="" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Missing Criteria" value={requirements.missingCriteria} suffix="" /></Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2, textAlign: 'center' }}>
            <ModuleHeader title="Requirement Quality Score" />
            <GaugeChart chartId="requirements.quality-gauge" value={requirements.qualityScore} label="Quality Score" size={200} />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Risk Distribution" />
            <DonutChart chartId="requirements.risk-distribution" data={requirements.riskDistribution} centerLabel="Total" centerValue={requirements.analysed} />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Compliance Impact" />
            <KpiCard label="Compliance-Tagged" value={requirements.complianceImpact} suffix="" compact />
            <HorizontalBarChart
              chartId="requirements.compliance-breakdown"
              data={requirements.complianceBreakdown.map((c) => ({ name: c.name, value: c.count * 8 }))}
              height={120}
              barColor={colors.warning}
            />
          </GlassCard>
        </Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Top Risk Requirements" />
        {requirements.topRiskRequirements.map((req) => (
          <DrilldownTableRow
            key={req.id}
            chartId="requirements.top-risk"
            segment={req.id}
            label={req.title}
            value={req.id}
            sx={{ display: 'flex', gap: 2, py: 1, borderBottom: `1px solid ${colors.border.subtle}` }}
          >
            <Typography variant="caption" sx={{ fontWeight: 700, minWidth: 100 }}>{req.id}</Typography>
            <Typography variant="caption" sx={{ flex: 1 }}>{req.title}</Typography>
            <Typography variant="caption" color="text.secondary">{req.impact}</Typography>
            <SeverityChip severity={req.risk} />
          </DrilldownTableRow>
        ))}
      </GlassCard>
    </Box>
  );
}
