import { Box } from '@mui/material';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { colors } from '../../theme/colors';

interface Series {
  key: string;
  color: string;
  name: string;
}

interface MultiLineChartProps {
  data: Record<string, string | number>[];
  series: Series[];
  height?: number;
}

export function MultiLineChart({ data, series, height = 200 }: MultiLineChartProps) {
  return (
    <Box sx={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            {series.map((s) => (
              <linearGradient key={s.key} id={`area-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={s.color} stopOpacity={0.3} />
                <stop offset="100%" stopColor={s.color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.border.subtle} vertical={false} />
          <XAxis dataKey="month" tick={{ fill: colors.text.muted, fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis domain={[70, 100]} tick={{ fill: colors.text.muted, fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{
              background: colors.bg.secondary,
              border: `1px solid ${colors.border.subtle}`,
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            iconType="circle"
            iconSize={8}
          />
          {series.map((s) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              fill={`url(#area-${s.key})`}
              dot={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </Box>
  );
}
