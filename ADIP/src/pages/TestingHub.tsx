import { Box, Grid, Typography, LinearProgress } from '@mui/material';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, CartesianGrid, Tooltip, Legend } from 'recharts';
import { KpiCard } from '../components/common/KpiCard';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { HeatmapGrid } from '../components/charts/HeatmapGrid';
import { AIInsightBox } from '../components/common/AIInsightBox';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';
import { AnalyzeWithAIPanel } from '../components/workflow/AnalyzeWithAIPanel';
import { TestingIntakeWorkflow } from '../components/testing/TestingIntakeWorkflow';

export function TestingHub() {
  const { testing } = useFilteredSimulation();

  return (
    <Box>
      <AnalyzeWithAIPanel
        phase="testing"
        title="Testing Analysis"
        subtitle="Test planning, regression packs, and coverage"
        placeholder="e.g. UPI settlement regression, payment flow test strategy..."
        glow="green"
      />

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 2 }}><KpiCard label="Total Tests" value={testing.totalTests.toLocaleString()} suffix="" compact /></Grid>
        <Grid size={{ xs: 6, md: 2 }}><KpiCard label="Manual Tests" value={testing.manualTests.toLocaleString()} suffix="" compact /></Grid>
        <Grid size={{ xs: 6, md: 2 }}><KpiCard label="Coverage" value={testing.coverage} trend={0.5} compact /></Grid>
        <Grid size={{ xs: 6, md: 2 }}><KpiCard label="Automation" value={testing.automation} trend={1.2} compact /></Grid>
        <Grid size={{ xs: 6, md: 2 }}><KpiCard label="Effectiveness" value={testing.effectiveness} compact /></Grid>
        <Grid size={{ xs: 6, md: 2 }}><KpiCard label="AI Recommended" value={testing.recommended} suffix="" compact /></Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Test Optimization Progress" />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <LinearProgress variant="determinate" value={testing.optimizationProgress} sx={{ flex: 1, height: 8, borderRadius: 4, '& .MuiLinearProgress-bar': { bgcolor: colors.primary } }} />
          <Typography variant="body2" sx={{ fontWeight: 700 }}>{testing.optimizationProgress}%</Typography>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
          Defect leakage: {testing.defectLeakage} · High-risk analysed: {testing.highRiskAnalyzed}
        </Typography>
      </GlassCard>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Coverage Heatmap" />
            <HeatmapGrid
              chartId="testing.coverage-heatmap"
              rows={testing.coverageHeatmap.map((r) => r.slice(1).map(Number))}
              columns={testing.heatmapEnvs}
              rowLabels={testing.coverageHeatmap.map((r) => String(r[0]))}
            />
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Defect Find vs Escape Trend" />
            <Box sx={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={testing.defectTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.border.subtle} />
                  <XAxis dataKey="week" tick={{ fill: colors.text.muted, fontSize: 11 }} />
                  <YAxis tick={{ fill: colors.text.muted, fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: colors.bg.secondary, borderRadius: 8, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="found" stroke={colors.primary} strokeWidth={2} dot={false} name="Found" />
                  <Line type="monotone" dataKey="escaped" stroke={colors.critical} strokeWidth={2} dot={false} name="Escaped" />
                </LineChart>
              </ResponsiveContainer>
            </Box>
            <AIInsightBox insight={testing.aiRecommendations[0]} actionLabel="View Recommendations" />
          </GlassCard>
        </Grid>
      </Grid>

      <TestingIntakeWorkflow />
    </Box>
  );
}
