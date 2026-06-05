import { Box, Grid, Typography, Switch, FormControlLabel } from '@mui/material';
import { GlassCard } from '../components/common/GlassCard';
import { ModuleHeader } from '../components/common/ModuleHeader';
import { StatusDot } from '../components/common/StatusDot';
import { useFilteredSimulation } from '../hooks/useFilteredSimulation';
import { colors } from '../theme/colors';

export function Administration() {
  const { administration } = useFilteredSimulation();

  return (
    <Box>
      <Grid container spacing={1.5}>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Operations Manager Settings" subtitle="Persona: Operations Manager (fixed)" />
            {[
              { label: 'Live Simulation (15s)', default: true },
              { label: 'Incident Alert Push', default: true },
              { label: 'Batch Failure Alerts', default: true },
              { label: 'Domain Filter Persistence', default: true },
            ].map((cfg) => (
              <FormControlLabel
                key={cfg.label}
                control={<Switch defaultChecked={cfg.default} size="small" />}
                label={<Typography variant="caption">{cfg.label}</Typography>}
                sx={{ display: 'flex', justifyContent: 'space-between', ml: 0, mb: 1, width: '100%' }}
              />
            ))}
          </GlassCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <GlassCard sx={{ p: 2 }}>
            <ModuleHeader title="Operations Integrations" />
            {administration.integrations.map((int) => (
              <Box key={int.name} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.75, borderBottom: `1px solid ${colors.border.subtle}` }}>
                <StatusDot status={int.status} />
                <Typography variant="caption" sx={{ flex: 1 }}>{int.name}</Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>{int.lastSync}</Typography>
              </Box>
            ))}
          </GlassCard>
        </Grid>
      </Grid>

      <GlassCard sx={{ p: 2, mt: 1.5 }}>
        <ModuleHeader title="Supported Banking Domains" />
        {['Net Banking', 'Mobile Banking', 'Payments'].map((d) => (
          <Typography key={d} variant="caption" sx={{ display: 'block', py: 0.5 }}>
            • {d} — operational telemetry enabled
          </Typography>
        ))}
      </GlassCard>
    </Box>
  );
}
