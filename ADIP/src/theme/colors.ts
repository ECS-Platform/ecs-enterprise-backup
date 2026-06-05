export const colors = {
  bg: {
    primary: '#040B1F',
    secondary: '#07132D',
    tertiary: '#0A1738',
    card: 'rgba(10, 23, 56, 0.65)',
    cardHover: 'rgba(14, 30, 70, 0.75)',
    glass: 'rgba(8, 18, 45, 0.55)',
  },
  primary: '#3B82F6',
  secondary: '#8B5CF6',
  success: '#22C55E',
  warning: '#F59E0B',
  critical: '#EF4444',
  info: '#06B6D4',
  text: {
    primary: '#F1F5F9',
    secondary: '#94A3B8',
    muted: '#64748B',
  },
  border: {
    subtle: 'rgba(59, 130, 246, 0.15)',
    glow: 'rgba(59, 130, 246, 0.35)',
    purple: 'rgba(139, 92, 246, 0.25)',
  },
  chart: {
    blue: '#3B82F6',
    purple: '#8B5CF6',
    cyan: '#06B6D4',
    green: '#22C55E',
    amber: '#F59E0B',
    red: '#EF4444',
    pink: '#EC4899',
  },
} as const;

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low';

export const riskColors: Record<RiskLevel, string> = {
  critical: colors.critical,
  high: '#F97316',
  medium: colors.warning,
  low: colors.primary,
};
