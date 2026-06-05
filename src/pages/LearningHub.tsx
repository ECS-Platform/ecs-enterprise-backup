import { Box, Grid, Typography, Tabs, Tab } from '@mui/material';
import { useState } from 'react';
import { KpiCard } from '../components/common/KpiCard';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { SeverityChip } from '../components/common/SeverityChip';
import { AIInsightBox } from '../components/common/AIInsightBox';
import { colors } from '../theme/colors';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';

export function LearningHub() {
  const [tab, setTab] = useState(0);
  const { learning } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Lessons Learned" value={learning.lessonsLearned} trend={10} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Reusable Assets" value={learning.reusableAssets} trend={6} /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Similar Incidents" value={learning.similarIncidents} suffix="" /></Grid>
        <Grid size={{ xs: 6, md: 3 }}><KpiCard label="Tech Debt Logged" value={learning.techDebtIdentified} suffix="" /></Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ minHeight: 32, mb: 2 }}>
          <Tab label="Lessons from Incidents" />
          <Tab label="Reusable Assets" />
          <Tab label="Similar Changes" />
        </Tabs>
        {tab === 0 && learning.incidents.map((inc) => (
          <Box key={inc.title} sx={{ display: 'flex', gap: 2, py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}>
            <Typography variant="caption" sx={{ flex: 1 }}>{inc.title}</Typography>
            <Typography variant="caption" color="text.secondary">{inc.date}</Typography>
            <SeverityChip severity={inc.severity} />
          </Box>
        ))}
        {tab === 1 && learning.knowledgeBase.map((kb) => (
          <Box key={kb.title} sx={{ display: 'flex', gap: 2, py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}>
            <Typography variant="caption" sx={{ flex: 1, fontWeight: 600 }}>{kb.title}</Typography>
            <Typography variant="caption" color="text.secondary">{kb.category}</Typography>
            <Typography variant="caption" sx={{ color: colors.primary }}>{kb.views} views</Typography>
          </Box>
        ))}
        {tab === 2 && learning.recentLessons.map((l) => (
          <Box key={l.text} sx={{ mb: 1 }}>
            <Typography variant="caption">{l.text}</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem', display: 'block' }}>{l.time}</Typography>
          </Box>
        ))}
      </GlassCard>

      <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 8 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Knowledge Base" />
            {learning.knowledgeBase.map((kb) => (
              <Box key={kb.title} sx={{ py: 1, borderBottom: `1px solid ${colors.border.subtle}` }}>
                <Typography variant="caption" sx={{ fontWeight: 600 }}>{kb.title}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>{kb.category}</Typography>
              </Box>
            ))}
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Learning Analytics" />
            {learning.analytics.map((m) => (
              <Box key={m.label} sx={{ display: 'flex', justifyContent: 'space-between', py: 1, borderBottom: `1px solid ${colors.border.subtle}` }}>
                <Typography variant="caption">{m.label}</Typography>
                <Typography variant="caption" sx={{ fontWeight: 700, color: colors.success }}>{m.value}</Typography>
              </Box>
            ))}
            <AIInsightBox insight="UPI settlement playbook reused 8 times post-incident — highest adoption this quarter." />
          </GlassCard>
        </Grid>
      </Grid>
    </Box>
  );
}
