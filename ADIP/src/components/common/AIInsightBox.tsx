import { Box, Typography, Button } from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { colors } from '../../theme/colors';

interface AIInsightBoxProps {
  title?: string;
  insight: string;
  actionLabel?: string;
}

export function AIInsightBox({ title = 'AI Recommendation', insight, actionLabel }: AIInsightBoxProps) {
  return (
    <Box
      sx={{
        mt: 1.5,
        p: 1.5,
        borderRadius: 1.5,
        background: `linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(59,130,246,0.08) 100%)`,
        border: `1px solid ${colors.border.purple}`,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.75 }}>
        <AutoAwesomeIcon sx={{ fontSize: 16, color: colors.secondary }} />
        <Typography variant="caption" sx={{ fontWeight: 700, color: colors.secondary, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {title}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.78rem', lineHeight: 1.5 }}>
        {insight}
      </Typography>
      {actionLabel && (
        <Button size="small" variant="outlined" sx={{ mt: 1, fontSize: '0.7rem', borderColor: colors.primary, color: colors.primary }}>
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}
