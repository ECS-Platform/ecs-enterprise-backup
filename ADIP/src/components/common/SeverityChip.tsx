import { Chip } from '@mui/material';
import { riskColors } from '../../theme/colors';
import type { RiskLevel } from '../../theme/colors';

interface SeverityChipProps {
  severity: RiskLevel | string;
  size?: 'small' | 'medium';
}

const labelMap: Record<string, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

export function SeverityChip({ severity, size = 'small' }: SeverityChipProps) {
  const key = severity.toLowerCase();
  const color = riskColors[key as RiskLevel] || riskColors.medium;

  return (
    <Chip
      label={labelMap[key] || severity}
      size={size}
      sx={{
        height: size === 'small' ? 20 : 24,
        fontSize: '0.65rem',
        fontWeight: 700,
        bgcolor: `${color}22`,
        color,
        border: `1px solid ${color}44`,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
      }}
    />
  );
}
