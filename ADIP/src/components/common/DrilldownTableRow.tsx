import type { ReactNode } from 'react';
import { Box } from '@mui/material';
import type { BoxProps } from '@mui/material';
import { colors } from '../../theme/colors';
import { useSimulation } from '../../context/SimulationContext';

interface DrilldownTableRowProps extends BoxProps {
  chartId: string;
  segment: string;
  label: string;
  value: string | number;
  suffix?: string;
  children: ReactNode;
}

export function DrilldownTableRow({
  chartId,
  segment,
  label,
  value,
  suffix,
  children,
  sx,
  ...props
}: DrilldownTableRowProps) {
  const { openKpiDrilldown } = useSimulation();

  const handleClick = () => {
    openKpiDrilldown({ chartId, segment, label, value, suffix });
  };

  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      sx={{
        cursor: 'pointer',
        transition: 'background-color 0.15s',
        '&:hover': { bgcolor: colors.bg.glass },
        '&:focus-visible': { outline: `2px solid ${colors.primary}`, outlineOffset: -2 },
        ...sx,
      }}
      {...props}
    >
      {children}
    </Box>
  );
}
