import { Box, Typography, Tooltip } from '@mui/material';
import { colors } from '../../theme/colors';

interface HeatmapGridProps {
  rows: number[][];
  columns: string[];
  rowLabels: string[];
}

function cellColor(value: number): string {
  if (value >= 90) return colors.success;
  if (value >= 75) return colors.warning;
  return colors.critical;
}

export function HeatmapGrid({ rows, columns, rowLabels }: HeatmapGridProps) {
  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 0.5, mb: 0.5, pl: 8 }}>
        {columns.map((col) => (
          <Typography key={col} variant="caption" sx={{ flex: 1, textAlign: 'center', fontSize: '0.65rem', color: colors.text.muted }}>
            {col}
          </Typography>
        ))}
      </Box>
      {rows.map((row, ri) => (
        <Box key={rowLabels[ri]} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
          <Typography variant="caption" sx={{ width: 72, fontSize: '0.65rem', color: colors.text.secondary, flexShrink: 0 }}>
            {rowLabels[ri]}
          </Typography>
          {row.map((num, ci) => {
            const bg = cellColor(num);
            return (
              <Tooltip key={ci} title={`${rowLabels[ri]} / ${columns[ci]}: ${num}%`}>
                <Box
                  sx={{
                    flex: 1,
                    height: 28,
                    borderRadius: 0.5,
                    bgcolor: `${bg}33`,
                    border: `1px solid ${bg}55`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'default',
                    transition: 'transform 0.15s',
                    '&:hover': { transform: 'scale(1.05)' },
                  }}
                >
                  <Typography variant="caption" sx={{ fontSize: '0.6rem', fontWeight: 600, color: bg }}>
                    {num}
                  </Typography>
                </Box>
              </Tooltip>
            );
          })}
        </Box>
      ))}
    </Box>
  );
}
