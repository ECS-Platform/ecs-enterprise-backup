import { Box, Typography } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { colors } from '../../theme/colors';

interface DonutChartProps {
  data: { name: string; value: number; color: string }[];
  centerLabel?: string;
  centerValue?: string | number;
  height?: number;
}

export function DonutChart({ data, centerLabel, centerValue, height = 160 }: DonutChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <Box sx={{ position: 'relative', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={2}
            dataKey="value"
            stroke="none"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: colors.bg.secondary,
              border: `1px solid ${colors.border.subtle}`,
              borderRadius: 8,
              fontSize: 12,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          textAlign: 'center',
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1 }}>
          {centerValue ?? total}
        </Typography>
        {centerLabel && (
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
            {centerLabel}
          </Typography>
        )}
      </Box>
    </Box>
  );
}
