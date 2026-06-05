import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box, List, ListItemButton, ListItemIcon, ListItemText, Typography, Divider,
} from '@mui/material';
import { motion } from 'framer-motion';
import DashboardIcon from '@mui/icons-material/Dashboard';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import AssignmentIcon from '@mui/icons-material/Assignment';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import CodeIcon from '@mui/icons-material/Code';
import ScienceIcon from '@mui/icons-material/Science';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import CloudIcon from '@mui/icons-material/Cloud';
import SettingsIcon from '@mui/icons-material/Settings';
import GavelIcon from '@mui/icons-material/Gavel';
import SchoolIcon from '@mui/icons-material/School';
import AssessmentIcon from '@mui/icons-material/Assessment';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import { colors } from '../../theme/colors';
import { layout } from '../../theme/theme';

const navItems = [
  { path: '/', label: 'Executive', icon: DashboardIcon },
  { path: '/delivery', label: 'Delivery', icon: LocalShippingIcon },
  { path: '/requirements', label: 'Requirements', icon: AssignmentIcon },
  { path: '/architecture', label: 'Architecture', icon: AccountTreeIcon },
  { path: '/development', label: 'Development', icon: CodeIcon },
  { path: '/testing', label: 'Testing', icon: ScienceIcon },
  { path: '/release', label: 'Release', icon: RocketLaunchIcon },
  { path: '/production', label: 'Production', icon: CloudIcon },
  { path: '/operations', label: 'Operations', icon: SettingsIcon },
  { path: '/governance', label: 'Governance', icon: GavelIcon },
  { path: '/learning', label: 'Learning', icon: SchoolIcon },
  { path: '/reports', label: 'Reports', icon: AssessmentIcon },
  { path: '/administration', label: 'Administration', icon: AdminPanelSettingsIcon },
];

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Box
      component={motion.nav}
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4 }}
      sx={{
        width: layout.sidebarWidth,
        minWidth: layout.sidebarWidth,
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        zIndex: 1200,
        background: `linear-gradient(180deg, ${colors.bg.secondary} 0%, ${colors.bg.primary} 100%)`,
        borderRight: `1px solid ${colors.border.subtle}`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <Box sx={{ p: 2, pb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 1.5,
              background: `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 16px ${colors.primary}44`,
            }}
          >
            <Typography sx={{ fontWeight: 800, fontSize: '0.75rem', color: '#fff' }}>AI</Typography>
          </Box>
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 800, letterSpacing: '0.08em', lineHeight: 1.2 }}>
              ADIP
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem' }}>
              Delivery Intelligence
            </Typography>
          </Box>
        </Box>
      </Box>
      <Divider sx={{ borderColor: colors.border.subtle }} />
      <List sx={{ flex: 1, py: 1, px: 1, overflow: 'auto' }}>
        {navItems.map((item) => {
          const active = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <ListItemButton
              key={item.path}
              onClick={() => navigate(item.path)}
              sx={{
                borderRadius: 1.5,
                mb: 0.25,
                py: 0.75,
                px: 1.5,
                bgcolor: active ? `${colors.primary}18` : 'transparent',
                borderLeft: active ? `3px solid ${colors.primary}` : '3px solid transparent',
                '&:hover': { bgcolor: `${colors.primary}12` },
              }}
            >
              <ListItemIcon sx={{ minWidth: 32, color: active ? colors.primary : colors.text.muted }}>
                <Icon sx={{ fontSize: 18 }} />
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                sx={{
                  '& .MuiListItemText-primary': {
                    fontSize: '0.8125rem',
                    fontWeight: active ? 600 : 400,
                    color: active ? colors.text.primary : colors.text.secondary,
                  },
                }}
              />
            </ListItemButton>
          );
        })}
      </List>
      <Box sx={{ p: 1.5, borderTop: `1px solid ${colors.border.subtle}` }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
          v2.4.1 · Production
        </Typography>
      </Box>
    </Box>
  );
}
