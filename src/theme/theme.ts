import { createTheme } from '@mui/material/styles';
import { colors } from './colors';

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: colors.primary },
    secondary: { main: colors.secondary },
    success: { main: colors.success },
    warning: { main: colors.warning },
    error: { main: colors.critical },
    background: {
      default: colors.bg.primary,
      paper: colors.bg.secondary,
    },
    text: {
      primary: colors.text.primary,
      secondary: colors.text.secondary,
    },
    divider: colors.border.subtle,
  },
  typography: {
    fontFamily: '"Inter", "Segoe UI", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontWeight: 700, letterSpacing: '-0.01em' },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600, fontSize: '1.125rem' },
    h5: { fontWeight: 600, fontSize: '1rem' },
    h6: { fontWeight: 600, fontSize: '0.875rem' },
    body2: { fontSize: '0.8125rem' },
    caption: { fontSize: '0.75rem', color: colors.text.muted },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          background: `linear-gradient(180deg, ${colors.bg.primary} 0%, ${colors.bg.secondary} 50%, ${colors.bg.tertiary} 100%)`,
          minHeight: '100vh',
        },
        '::-webkit-scrollbar': { width: 6, height: 6 },
        '::-webkit-scrollbar-track': { background: colors.bg.primary },
        '::-webkit-scrollbar-thumb': {
          background: colors.border.glow,
          borderRadius: 3,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          minHeight: 36,
          fontSize: '0.8125rem',
        },
      },
    },
  },
});

export const layout = {
  sidebarWidth: 240,
  topBarHeight: 56,
  aiAdvisorWidth: 300,
} as const;
