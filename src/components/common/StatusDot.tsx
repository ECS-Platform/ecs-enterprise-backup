import { Box } from '@mui/material';
import { colors } from '../../theme/colors';

const statusColors: Record<string, string> = {
  healthy: colors.success,
  degraded: colors.warning,
  critical: colors.critical,
  ready: colors.success,
  'at risk': colors.warning,
  investigating: colors.warning,
  mitigated: colors.info,
  resolved: colors.success,
  completed: colors.success,
  'in progress': colors.primary,
};

export function StatusDot({ status }: { status: string }) {
  const color = statusColors[status.toLowerCase()] || colors.text.muted;
  return (
    <Box
      sx={{
        width: 8,
        height: 8,
        borderRadius: '50%',
        bgcolor: color,
        boxShadow: `0 0 6px ${color}`,
        flexShrink: 0,
      }}
    />
  );
}
