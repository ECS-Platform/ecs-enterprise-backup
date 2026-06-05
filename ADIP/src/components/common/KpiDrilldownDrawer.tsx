import {
  Box,
  Drawer,
  IconButton,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import { colors } from '../../theme/colors';
import { layout } from '../../theme/theme';
import { SeverityChip } from './SeverityChip';
import { useSimulation } from '../../context/SimulationContext';

const DRAWER_WIDTH = 380;

function SectionTitle({ children }: { children: string }) {
  return (
    <Typography
      variant="caption"
      sx={{
        fontWeight: 700,
        color: colors.secondary,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        fontSize: '0.65rem',
        display: 'block',
        mb: 1,
      }}
    >
      {children}
    </Typography>
  );
}

function RecordRow({
  id,
  title,
  detail,
  meta,
  severity,
}: {
  id: string;
  title: string;
  detail?: string;
  meta?: string;
  severity?: string;
}) {
  return (
    <Box
      sx={{
        p: 1,
        mb: 0.75,
        borderRadius: 1,
        bgcolor: colors.bg.glass,
        border: `1px solid ${colors.border.subtle}`,
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}>
        <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem' }}>
          {id}
        </Typography>
        {severity && <SeverityChip severity={severity} />}
      </Box>
      <Typography variant="body2" sx={{ fontSize: '0.78rem', mt: 0.25, lineHeight: 1.4 }}>
        {title}
      </Typography>
      {detail && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', display: 'block', mt: 0.25 }}>
          {detail}
        </Typography>
      )}
      {meta && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', display: 'block', mt: 0.25 }}>
          {meta}
        </Typography>
      )}
    </Box>
  );
}

export function KpiDrilldownDrawer() {
  const { kpiDrilldown, closeKpiDrilldown } = useSimulation();
  const open = kpiDrilldown !== null;
  const payload = kpiDrilldown?.payload;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={closeKpiDrilldown}
      hideBackdrop={false}
      slotProps={{
        paper: {
          sx: {
            width: DRAWER_WIDTH,
            right: layout.aiAdvisorWidth,
            left: 'auto',
            background: `linear-gradient(180deg, ${colors.bg.tertiary} 0%, ${colors.bg.primary} 100%)`,
            borderLeft: `1px solid ${colors.border.subtle}`,
            boxShadow: `-8px 0 32px rgba(0,0,0,0.4)`,
          },
        },
      }}
      ModalProps={{
        sx: { zIndex: 1180 },
        slotProps: {
          backdrop: { sx: { backgroundColor: 'rgba(4, 11, 31, 0.45)' } },
        },
      }}
      sx={{
        '& .MuiDrawer-paper': {
          position: 'fixed',
          right: layout.aiAdvisorWidth,
        },
      }}
    >
      {payload && (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <Box
            sx={{
              p: 2,
              borderBottom: `1px solid ${colors.border.subtle}`,
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              gap: 1,
            }}
          >
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', textTransform: 'uppercase' }}>
                KPI Drilldown
              </Typography>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.3 }}>
                {payload.label}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5, mt: 0.5 }}>
                <Typography variant="h5" sx={{ fontWeight: 700, color: colors.primary }}>
                  {payload.value}
                </Typography>
                {payload.suffix && (
                  <Typography variant="body2" color="text.secondary">
                    {payload.suffix}
                  </Typography>
                )}
              </Box>
            </Box>
            <IconButton size="small" onClick={closeKpiDrilldown} sx={{ color: colors.text.secondary }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>

          <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
            <SectionTitle>Historical Trend</SectionTitle>
            <Box
              sx={{
                height: 100,
                mb: 2,
                p: 1,
                borderRadius: 1,
                bgcolor: colors.bg.glass,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={payload.historicalTrend}>
                  <defs>
                    <linearGradient id="kpi-drilldown-trend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={colors.primary} stopOpacity={0.4} />
                      <stop offset="100%" stopColor={colors.primary} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke={colors.primary}
                    strokeWidth={1.5}
                    fill="url(#kpi-drilldown-trend)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Box>

            <SectionTitle>Source Records</SectionTitle>
            <Box sx={{ mb: 2 }}>
              {payload.sourceRecords.length > 0 ? (
                payload.sourceRecords.map((r) => (
                  <RecordRow
                    key={r.id}
                    id={r.id}
                    title={r.title}
                    detail={r.detail}
                    meta={r.meta}
                    severity={['critical', 'high', 'medium', 'low'].includes(r.meta?.toLowerCase() ?? '') ? r.meta : undefined}
                  />
                ))
              ) : (
                <Typography variant="caption" color="text.secondary">No source records available.</Typography>
              )}
            </Box>

            <SectionTitle>Supporting Evidence</SectionTitle>
            <Box sx={{ mb: 2 }}>
              {payload.supportingEvidence.map((line) => (
                <Typography
                  key={line}
                  variant="body2"
                  color="text.secondary"
                  sx={{ fontSize: '0.75rem', mb: 0.75, lineHeight: 1.5, pl: 1, borderLeft: `2px solid ${colors.border.purple}` }}
                >
                  {line}
                </Typography>
              ))}
            </Box>

            <SectionTitle>Related Applications</SectionTitle>
            <Box sx={{ mb: 2, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {payload.relatedApplications.map((app) => (
                <Box
                  key={app.name}
                  sx={{
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                    bgcolor: colors.bg.glass,
                    border: `1px solid ${colors.border.subtle}`,
                    fontSize: '0.72rem',
                  }}
                >
                  {app.name}
                  {app.status && (
                    <Typography component="span" variant="caption" sx={{ ml: 0.5, color: colors.text.muted }}>
                      · {app.status}
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>

            <SectionTitle>Related Incidents</SectionTitle>
            <Box sx={{ mb: 2 }}>
              {payload.relatedIncidents.map((inc) => (
                <RecordRow
                  key={inc.id}
                  id={inc.id}
                  title={inc.title}
                  detail={inc.domain}
                  severity={inc.severity}
                />
              ))}
            </Box>

            <SectionTitle>Related Releases</SectionTitle>
            <Box>
              {payload.relatedReleases.map((rel) => (
                <RecordRow
                  key={rel.id}
                  id={rel.id}
                  title={rel.name}
                  meta={`${rel.confidence}% · ${rel.risk} risk`}
                />
              ))}
            </Box>
          </Box>
        </Box>
      )}
    </Drawer>
  );
}
