import { Box, Typography } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { colors } from '../../theme/colors';
import { useSimulation } from '../../context/SimulationContext';

interface CircularGaugeProps {
  value: number;
  label: string;
  size?: number;
  color?: string;
  chartId?: string;
}

export function CircularGauge({ value, label, size = 80, color, chartId }: CircularGaugeProps) {
  const { openKpiDrilldown } = useSimulation();
  const gaugeColor = color || (value >= 90 ? colors.success : value >= 70 ? colors.warning : colors.critical);
  const data = [{ value }, { value: 100 - value }];

  const handleClick = () => {
    if (!chartId) return;
    openKpiDrilldown({
      chartId,
      segment: label,
      label,
      value,
      suffix: '%',
    });
  };

  return (
    <Box
      role={chartId ? 'button' : undefined}
      tabIndex={chartId ? 0 : undefined}
      onClick={chartId ? handleClick : undefined}
      onKeyDown={chartId ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleClick(); } } : undefined}
      sx={{
        textAlign: 'center',
        width: size,
        cursor: chartId ? 'pointer' : 'default',
        '&:focus-visible': chartId ? { outline: `2px solid ${colors.primary}`, borderRadius: 1 } : {},
      }}
    >
      <Box sx={{ height: size * 0.7, position: 'relative' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="80%"
              startAngle={180}
              endAngle={0}
              innerRadius="65%"
              outerRadius="95%"
              dataKey="value"
              stroke="none"
            >
              <Cell fill={gaugeColor} />
              <Cell fill="rgba(255,255,255,0.06)" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <Typography
          variant="body2"
          sx={{ position: 'absolute', bottom: 2, left: '50%', transform: 'translateX(-50%)', fontWeight: 700, fontSize: '0.8rem', color: gaugeColor }}
        >
          {value}%
        </Typography>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
        {label}
      </Typography>
    </Box>
  );
}
