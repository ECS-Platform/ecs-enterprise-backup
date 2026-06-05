import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { colors } from '../../theme/colors';

interface HorizontalBarChartProps {
  data: { name: string; value: number }[];
  height?: number;
  barColor?: string;
}

export function HorizontalBarChart({ data, height = 160, barColor = colors.primary }: HorizontalBarChartProps) {
  return (
    <Box sx={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis
            type="category"
            dataKey="name"
            width={110}
            tick={{ fill: colors.text.secondary, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={14}>
            {data.map((_, i) => (
              <Cell key={i} fill={barColor} fillOpacity={0.85 - i * 0.05} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {data.map((d) => (
        <Typography key={d.name} variant="caption" sx={{ display: 'none' }}>
          {d.value}%
        </Typography>
      ))}
    </Box>
  );
}
