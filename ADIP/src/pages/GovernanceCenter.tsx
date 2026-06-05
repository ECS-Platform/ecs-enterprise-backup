import { Box, Grid, Typography, LinearProgress } from '@mui/material';
import { KpiCard } from '../components/common/KpiCard';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { DonutChart } from '../components/charts/DonutChart';
import { CircularGauge } from '../components/charts/CircularGauge';
import { GaugeChart } from '../components/charts/GaugeChart';
import { HorizontalBarChart } from '../components/charts/HorizontalBarChart';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function GovernanceCenter() {
  const { governance } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Audit Findings" value={governance.auditObservations} suffix="" compact /></Grid>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="VAPT Findings" value={governance.vaptFindings} suffix="" trend={-8} compact /></Grid>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Policy Violations" value={governance.policyViolations} suffix="" compact /></Grid>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Security Findings" value={governance.securityFindings} suffix="" compact /></Grid>
        <Grid size={{ xs: 6, md: 2.4 }}><KpiCard label="Governance Score" value={governance.governanceScore} trend={1} compact /></Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Finding Severity" />
            <DonutChart data={governance.findingSeverity} centerLabel="Total" height={160} />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2, textAlign: 'center' }}>
            <ModuleHeader title="Governance Health" />
            <GaugeChart value={governance.governanceScore} label="Score" size={180} />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Compliance Posture" />
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 3 }}>
              <CircularGauge value={governance.baselineCompliance} label="Baseline" />
              <CircularGauge value={governance.policyCompliance} label="Policy" />
            </Box>
          </GlassCard>
        </Grid>
      </Grid>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Regulatory Compliance" />
            <HorizontalBarChart data={governance.complianceStandards.map((s) => ({ name: s.name, value: s.score }))} height={160} barColor={colors.success} />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Top Governance Observations" />
            {governance.topFindings.map((f) => (
              <Box key={f.title} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}>
                <Typography variant="caption" sx={{ flex: 1, mr: 1 }}>{f.title}</Typography>
                <SeverityChip severity={f.severity} />
              </Box>
            ))}
            {governance.auditTrail.map((a) => (
              <Typography key={a.event} variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.75, fontSize: '0.65rem' }}>
                {a.time} — {a.event}
              </Typography>
            ))}
          </GlassCard>
        </Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Compliance Dashboard" />
        {governance.complianceStandards.map((s) => (
          <Box key={s.name} sx={{ mb: 1.5 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.25 }}>
              <Typography variant="caption">{s.name}</Typography>
              <Typography variant="caption" sx={{ fontWeight: 700 }}>{s.score}%</Typography>
            </Box>
            <LinearProgress variant="determinate" value={s.score} sx={{ height: 6, borderRadius: 3, '& .MuiLinearProgress-bar': { bgcolor: s.score >= 90 ? colors.success : colors.warning } }} />
          </Box>
        ))}
      </GlassCard>
    </Box>
  );
}
