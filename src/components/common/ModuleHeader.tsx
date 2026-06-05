import { Box, Typography, IconButton } from '@mui/material';
import { Search, OpenInFull, Settings } from '@mui/icons-material';
import { colors } from '../../theme/colors';

interface ModuleHeaderProps {
  number?: number;
  title: string;
  subtitle?: string;
}

export function ModuleHeader({ number, title, subtitle }: ModuleHeaderProps) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
      <Box>
        <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '0.9rem' }}>
          {number !== undefined && (
            <Box component="span" sx={{ color: colors.primary, mr: 1 }}>
              {number}.
            </Box>
          )}
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="caption" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </Box>
      <Box sx={{ display: 'flex', gap: 0.25 }}>
        <IconButton size="small" sx={{ color: colors.text.muted, p: 0.5 }}>
          <Search sx={{ fontSize: 16 }} />
        </IconButton>
        <IconButton size="small" sx={{ color: colors.text.muted, p: 0.5 }}>
          <OpenInFull sx={{ fontSize: 16 }} />
        </IconButton>
        <IconButton size="small" sx={{ color: colors.text.muted, p: 0.5 }}>
          <Settings sx={{ fontSize: 16 }} />
        </IconButton>
      </Box>
    </Box>
  );
}
