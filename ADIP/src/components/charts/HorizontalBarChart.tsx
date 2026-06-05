import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { colors } from '../../theme/colors';
import { useSimulation } from '../../context/SimulationContext';

interface HorizontalBarChartProps {
  data: { name: string; value: number }[];
  height?: number;
  barColor?: string;
  chartId?: string;
}

export function HorizontalBarChart({ data, height = 160, barColor = colors.primary, chartId }: HorizontalBarChartProps) {
  const { openKpiDrilldown } = useSimulation();

  const handleBarClick = (barData: { payload?: { name: string; value: number } }) => {
    if (!chartId || !barData?.payload) return;
    const { name, value } = barData.payload;
    openKpiDrilldown({
      chartId,
      segment: name,
      label: name,
      value,
      suffix: '%',
    });
  };

  return (
    <Box sx={{ height, cursor: chartId ? 'pointer' : 'default' }}>
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
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={14} onClick={handleBarClick}>
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
