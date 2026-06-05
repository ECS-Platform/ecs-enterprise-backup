import { Box } from '@mui/material';
import type { BoxProps } from '@mui/material';
import { motion } from 'framer-motion';
import { colors } from '../../theme/colors';

interface GlassCardProps extends BoxProps {
  glow?: 'blue' | 'purple' | 'green' | 'none';
  hover?: boolean;
  delay?: number;
}

const glowMap = {
  blue: `0 0 20px ${colors.border.glow}`,
  purple: `0 0 20px ${colors.border.purple}`,
  green: `0 0 20px rgba(34, 197, 94, 0.25)`,
  none: 'none',
};

export function GlassCard({ glow = 'none', hover = true, delay = 0, children, sx, ...props }: GlassCardProps) {
  return (
    <Box
      component={motion.div}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      whileHover={hover ? { y: -2, transition: { duration: 0.2 } } : undefined}
      sx={{
        background: colors.bg.card,
        backdropFilter: 'blur(12px)',
        border: `1px solid ${colors.border.subtle}`,
        borderRadius: 2,
        boxShadow: glowMap[glow],
        transition: 'border-color 0.2s, box-shadow 0.2s',
        '&:hover': hover
          ? { borderColor: colors.border.glow, boxShadow: `0 4px 24px rgba(0,0,0,0.3), ${glowMap[glow]}` }
          : {},
        ...sx,
      }}
      {...props}
    >
      {children}
    </Box>
  );
}
