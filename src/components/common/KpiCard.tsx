import { Box, Typography } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import { GlassCard } from './GlassCard';
import { colors } from '../../theme/colors';

interface KpiCardProps {
  label: string;
  value: string | number;
  suffix?: string;
  trend?: number;
  data?: { day: string; value: number }[];
  delay?: number;
  compact?: boolean;
}

export function KpiCard({ label, value, suffix = '%', trend, data, delay = 0, compact }: KpiCardProps) {
  const isPositive = trend !== undefined && trend >= 0;

  return (
    <GlassCard delay={delay} sx={{ p: compact ? 1.5 : 2, minHeight: compact ? 90 : 110 }}>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5, mt: 0.5 }}>
        <Typography variant={compact ? 'h5' : 'h4'} sx={{ fontWeight: 700, color: colors.text.primary }}>
          {value}
        </Typography>
        {suffix && (
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
            {suffix}
          </Typography>
        )}
      </Box>
      {trend !== undefined && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.25 }}>
          {isPositive ? (
            <TrendingUp sx={{ fontSize: 14, color: colors.success }} />
          ) : (
            <TrendingDown sx={{ fontSize: 14, color: colors.critical }} />
          )}
          <Typography variant="caption" sx={{ color: isPositive ? colors.success : colors.critical, fontWeight: 600 }}>
            {isPositive ? '+' : ''}{trend}%
          </Typography>
        </Box>
      )}
      {data && (
        <Box sx={{ height: 36, mt: 0.5, mx: -0.5 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.success} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={colors.success} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="value" stroke={colors.success} strokeWidth={1.5} fill={`url(#grad-${label})`} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      )}
    </GlassCard>
  );
}
