import { Box, Typography } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { colors } from '../../theme/colors';
import { useSimulation } from '../../context/SimulationContext';

interface GaugeChartProps {
  value: number;
  label?: string;
  sublabel?: string;
  size?: number;
  showGo?: boolean;
  chartId?: string;
}

export function GaugeChart({ value, label, sublabel, size = 180, showGo, chartId }: GaugeChartProps) {
  const { openKpiDrilldown } = useSimulation();
  const gaugeColor = value >= 90 ? colors.success : value >= 70 ? colors.warning : colors.critical;
  const data = [
    { value },
    { value: 100 - value },
  ];

  const handleClick = () => {
    if (!chartId) return;
    openKpiDrilldown({
      chartId,
      segment: label ?? 'gauge',
      label: label ?? 'Gauge',
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
        position: 'relative',
        width: size,
        height: size * 0.65,
        mx: 'auto',
        cursor: chartId ? 'pointer' : 'default',
        '&:focus-visible': chartId ? { outline: `2px solid ${colors.primary}`, borderRadius: 1 } : {},
      }}
    >
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
