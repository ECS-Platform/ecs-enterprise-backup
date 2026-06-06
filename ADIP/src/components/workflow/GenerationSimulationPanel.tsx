import { Box, LinearProgress, Typography } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { GlassCard } from '../common/GlassCard';
import { ModuleHeader } from '../common/ModuleHeader';
import { colors } from '../../theme/colors';

interface GenerationSimulationPanelProps {
  statusMessage: string;
  progress: number;
  activityLog: string[];
  visible: boolean;
  agentLabel?: string;
}

export function GenerationSimulationPanel({
  statusMessage,
  progress,
  activityLog,
  visible,
  agentLabel = 'AI Agent',
}: GenerationSimulationPanelProps) {
  if (!visible) return null;

  return (
    <GlassCard sx={{ p: 2, mt: 1.5 }} glow="purple">
      <ModuleHeader title="Generation in Progress" subtitle={agentLabel} />
      <Typography variant="body2" sx={{ fontSize: '0.8rem', color: colors.secondary, mb: 1.5, fontStyle: 'italic' }}>
        {statusMessage}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
        <Box sx={{ flex: 1 }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 8,
              borderRadius: 1,
              bgcolor: colors.bg.glass,
              '& .MuiLinearProgress-bar': {
                borderRadius: 1,
                background: `linear-gradient(90deg, ${colors.primary}, ${colors.secondary})`,
                transition: 'transform 0.4s ease',
              },
            }}
          />
        </Box>
        <Typography variant="caption" sx={{ fontWeight: 700, minWidth: 36, color: colors.primary }}>
          {progress}%
        </Typography>
      </Box>
      {activityLog.length > 0 && (
        <Box
          sx={{
            p: 1.5,
            borderRadius: 1,
            bgcolor: colors.bg.glass,
            border: `1px solid ${colors.border.subtle}`,
          }}
        >
          <Typography
            variant="caption"
            sx={{
              fontWeight: 700,
              color: colors.secondary,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontSize: '0.65rem',
              display: 'block',
              mb: 1,
            }}
          >
            Activity Log
          </Typography>
          {activityLog.map((entry) => (
            <Box key={entry} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, py: 0.35 }}>
              <CheckCircleIcon sx={{ fontSize: 14, color: colors.success }} />
              <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>
                {entry}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </GlassCard>
  );
}
