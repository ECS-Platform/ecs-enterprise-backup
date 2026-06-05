import { Box, Typography } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { colors } from '../../theme/colors';

interface GaugeChartProps {
  value: number;
  label?: string;
  sublabel?: string;
  size?: number;
  showGo?: boolean;
}

export function GaugeChart({ value, label, sublabel, size = 180, showGo }: GaugeChartProps) {
  const gaugeColor = value >= 90 ? colors.success : value >= 70 ? colors.warning : colors.critical;
  const data = [
    { value },
    { value: 100 - value },
  ];

  return (
    <Box sx={{ position: 'relative', width: size, height: size * 0.65, mx: 'auto' }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="90%"
            startAngle={180}
            endAngle={0}
            innerRadius="70%"
            outerRadius="100%"
            dataKey="value"
            stroke="none"
          >
            <Cell fill={gaugeColor} />
            <Cell fill="rgba(255,255,255,0.06)" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <Box sx={{ position: 'absolute', bottom: 8, left: '50%', transform: 'translateX(-50%)', textAlign: 'center' }}>
        <Typography variant="h4" sx={{ fontWeight: 700, color: gaugeColor, lineHeight: 1 }}>
          {value}%
        </Typography>
        {label && (
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            {label}
          </Typography>
        )}
        {showGo && value >= 85 && (
          <Box
            sx={{
              mt: 0.5,
              px: 2,
              py: 0.25,
              borderRadius: 1,
              bgcolor: `${colors.success}22`,
              border: `1px solid ${colors.success}`,
              color: colors.success,
              fontWeight: 800,
              fontSize: '0.85rem',
              boxShadow: `0 0 12px ${colors.success}44`,
            }}
          >
            GO
          </Box>
        )}
        {sublabel && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25, fontSize: '0.65rem' }}>
            {sublabel}
          </Typography>
        )}
      </Box>
    </Box>
  );
}
