import { useState } from 'react';
import {
  Box,
  Drawer,
  IconButton,
  Typography,
  Button,
  Tooltip,
  Chip,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DownloadIcon from '@mui/icons-material/Download';
import CheckIcon from '@mui/icons-material/Check';
import { colors } from '../../theme/colors';
import { layout } from '../../theme/theme';
import { SeverityChip } from './SeverityChip';
import { useSimulation } from '../../context/SimulationContext';
import { formatSummaryAsText } from '../../services/executiveSummaryEngine.js';
import type { ActionItem, HealthBand } from '../../types/executiveSummary';

const DRAWER_WIDTH = 440;

function SectionTitle({ index, children, accent }: { index: number; children: string; accent?: string }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
      <Box
        sx={{
          width: 18,
          height: 18,
          borderRadius: '50%',
          bgcolor: colors.secondary,
          color: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '0.65rem',
          fontWeight: 700,
        }}
      >
        {index}
      </Box>
      <Typography
        variant="caption"
        sx={{
          fontWeight: 700,
          color: colors.secondary,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          fontSize: '0.7rem',
          flex: 1,
        }}
      >
        {children}
      </Typography>
      {accent && (
        <Typography variant="caption" sx={{ fontSize: '0.7rem', color: colors.text.secondary, fontWeight: 600 }}>
          {accent}
        </Typography>
      )}
    </Box>
  );
}

function Paragraph({ children }: { children: string }) {
  return (
    <Typography
      variant="body2"
      color="text.secondary"
      sx={{ fontSize: '0.78rem', lineHeight: 1.55, mb: 1.25 }}
    >
      {children}
    </Typography>
  );
}

function bandColor(b: HealthBand) {
  if (b === 'Healthy') return colors.success;
  if (b === 'Watch') return colors.warning;
  return colors.critical;
}

function priorityColor(p: ActionItem['priority']) {
  if (p === 'P0') return colors.critical;
  if (p === 'P1') return colors.warning;
  return colors.primary;
}

export function ExecutiveSummaryDrawer() {
  const { executiveSummary, closeExecutiveSummary } = useSimulation();
  const open = executiveSummary !== null;
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!executiveSummary) return;
    const text = formatSummaryAsText(executiveSummary);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch { /* no-op */ }
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    }
  };

  const handleExport = () => {
    if (!executiveSummary) return;
    const text = formatSummaryAsText(executiveSummary);
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ts = new Date(executiveSummary.generatedAt)
      .toISOString()
      .replace(/[:.]/g, '-')
      .replace('T', '_')
      .slice(0, 19);
    a.href = url;
    a.download = `executive-summary_${ts}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={closeExecutiveSummary}
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
        sx: { zIndex: 1185 },
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
      {executiveSummary && (
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
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Executive Summary
              </Typography>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.3, mt: 0.25 }}>
                {executiveSummary.headline}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', mt: 0.5, display: 'block' }}>
                Generated {new Date(executiveSummary.generatedAt).toLocaleTimeString()} ·
                Tick #{executiveSummary.simulationTick}
                {executiveSummary.simulatedTime ? ` · Sim ${executiveSummary.simulatedTime}` : ''}
              </Typography>
            </Box>
            <IconButton size="small" onClick={closeExecutiveSummary} sx={{ color: colors.text.secondary }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>

          <Box
            sx={{
              px: 2,
              py: 1,
              display: 'flex',
              gap: 1,
              borderBottom: `1px solid ${colors.border.subtle}`,
              bgcolor: colors.bg.glass,
            }}
          >
            <Tooltip title={copied ? 'Copied' : 'Copy summary to clipboard'}>
              <Button
                size="small"
                variant="outlined"
                startIcon={copied ? <CheckIcon sx={{ fontSize: 14 }} /> : <ContentCopyIcon sx={{ fontSize: 14 }} />}
                onClick={handleCopy}
                sx={{
                  fontSize: '0.7rem',
                  borderColor: colors.border.subtle,
                  color: copied ? colors.success : colors.text.primary,
                  '&:hover': { borderColor: colors.primary },
                }}
              >
                {copied ? 'Copied' : 'Copy'}
              </Button>
            </Tooltip>
            <Tooltip title="Export summary as .txt file">
              <Button
                size="small"
                variant="outlined"
                startIcon={<DownloadIcon sx={{ fontSize: 14 }} />}
                onClick={handleExport}
                sx={{
                  fontSize: '0.7rem',
                  borderColor: colors.border.subtle,
                  color: colors.text.primary,
                  '&:hover': { borderColor: colors.primary },
                }}
              >
                Export .txt
              </Button>
            </Tooltip>
          </Box>

          <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
            {/* 1. Overall Health Score */}
            <SectionTitle
              index={1}
              accent={`${executiveSummary.overallHealthScore.score}% ${executiveSummary.overallHealthScore.label}`}
            >
              Overall Health Score
            </SectionTitle>
            <Paragraph>{executiveSummary.overallHealthScore.narrative}</Paragraph>
            <Box sx={{ mb: 2 }}>
              {executiveSummary.overallHealthScore.breakdown.map((b) => (
                <Box
                  key={b.name}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    py: 0.5,
                    borderBottom: `1px solid ${colors.border.subtle}`,
                  }}
                >
                  <Typography variant="caption" sx={{ fontSize: '0.72rem' }}>
                    {b.name}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography
                      variant="caption"
                      sx={{ fontSize: '0.72rem', fontWeight: 700, minWidth: 36, textAlign: 'right' }}
                    >
                      {b.value}%
                    </Typography>
                    <Box
                      sx={{
                        px: 0.75,
                        py: 0.25,
                        borderRadius: 0.5,
                        bgcolor: `${bandColor(b.status)}22`,
                        color: bandColor(b.status),
                        fontSize: '0.6rem',
                        fontWeight: 700,
                        minWidth: 70,
                        textAlign: 'center',
                      }}
                    >
                      {b.status}
                    </Box>
                  </Box>
                </Box>
              ))}
            </Box>

            {/* 2. Key Risks */}
            <SectionTitle index={2} accent={`${executiveSummary.keyRisks.items.length} flagged`}>
              Key Risks
            </SectionTitle>
            <Paragraph>{executiveSummary.keyRisks.narrative}</Paragraph>
            <Box sx={{ mb: 2 }}>
              {executiveSummary.keyRisks.items.length === 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.72rem' }}>
                  No elevated risks this cycle.
                </Typography>
              )}
              {executiveSummary.keyRisks.items.map((r) => (
                <Box
                  key={`${r.title}-${r.source}`}
                  sx={{
                    p: 1,
                    mb: 0.75,
                    borderRadius: 1,
                    bgcolor: colors.bg.glass,
                    border: `1px solid ${colors.border.subtle}`,
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}>
                    <Typography variant="body2" sx={{ fontSize: '0.76rem', fontWeight: 600 }}>
                      {r.title}
                    </Typography>
                    <SeverityChip severity={r.severity} />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.65rem', mt: 0.5 }}>
                    Impact: {r.impact}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.65rem' }}>
                    Source: {r.source}
                  </Typography>
                </Box>
              ))}
            </Box>

            {/* 3. Key Achievements */}
            <SectionTitle index={3} accent={`${executiveSummary.keyAchievements.items.length} noted`}>
              Key Achievements
            </SectionTitle>
            <Paragraph>{executiveSummary.keyAchievements.narrative}</Paragraph>
            <Box sx={{ mb: 2 }}>
              {executiveSummary.keyAchievements.items.map((a) => (
                <Box
                  key={a}
                  sx={{
                    pl: 1,
                    borderLeft: `2px solid ${colors.success}`,
                    mb: 0.75,
                  }}
                >
                  <Typography variant="caption" sx={{ fontSize: '0.74rem', lineHeight: 1.5 }}>
                    {a}
                  </Typography>
                </Box>
              ))}
            </Box>

            {/* 4. Critical Incidents */}
            <SectionTitle index={4} accent={`${executiveSummary.criticalIncidents.items.length} listed`}>
              Critical Incidents
            </SectionTitle>
            <Paragraph>{executiveSummary.criticalIncidents.narrative}</Paragraph>
            <Box sx={{ mb: 2 }}>
              {executiveSummary.criticalIncidents.items.length === 0 ? (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.72rem' }}>
                  No critical or high-severity incidents in scope.
                </Typography>
              ) : (
                executiveSummary.criticalIncidents.items.map((i) => (
                  <Box
                    key={i.id}
                    sx={{
                      p: 1,
                      mb: 0.75,
                      borderRadius: 1,
                      bgcolor: colors.bg.glass,
                      border: `1px solid ${colors.border.subtle}`,
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem' }}>
                        {i.id}
                      </Typography>
                      <SeverityChip severity={i.severity} />
                    </Box>
                    <Typography variant="body2" sx={{ fontSize: '0.76rem', mt: 0.25 }}>
                      {i.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                      {i.domain} · {i.duration} · {i.status}
                    </Typography>
                  </Box>
                ))
              )}
            </Box>

            {/* 5. Release Status */}
            <SectionTitle
              index={5}
              accent={`${executiveSummary.releaseStatus.goNoGo} · ${executiveSummary.releaseStatus.confidence}%`}
            >
              Release Status
            </SectionTitle>
            <Paragraph>{executiveSummary.releaseStatus.narrative}</Paragraph>
            <Box sx={{ mb: 2 }}>
              {executiveSummary.releaseStatus.items.map((r) => (
                <Box
                  key={r.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    py: 0.5,
                    borderBottom: `1px solid ${colors.border.subtle}`,
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem', minWidth: 90 }}>
                    {r.id}
                  </Typography>
                  <Typography variant="caption" sx={{ flex: 1, fontSize: '0.72rem' }}>
                    {r.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                    {r.domain}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: 700,
                      fontSize: '0.7rem',
                      color: r.confidence >= 90 ? colors.success : colors.warning,
                    }}
                  >
                    {r.confidence}%
                  </Typography>
                  <SeverityChip severity={r.risk} />
                </Box>
              ))}
            </Box>

            {/* 6. Governance Status */}
            <SectionTitle index={6} accent={`${executiveSummary.governanceStatus.score}%`}>
              Governance Status
            </SectionTitle>
            <Paragraph>{executiveSummary.governanceStatus.narrative}</Paragraph>
            <Box sx={{ mb: 2 }}>
              {executiveSummary.governanceStatus.bullets.map((b) => (
                <Box
                  key={b}
                  sx={{
                    pl: 1,
                    borderLeft: `2px solid ${colors.border.purple}`,
                    mb: 0.5,
                  }}
                >
                  <Typography variant="caption" sx={{ fontSize: '0.72rem', lineHeight: 1.5 }}>
                    {b}
                  </Typography>
                </Box>
              ))}
            </Box>

            {/* 7. Recommended Actions */}
            <SectionTitle index={7} accent={`${executiveSummary.recommendedActions.items.length} actions`}>
              Recommended Actions
            </SectionTitle>
            <Paragraph>{executiveSummary.recommendedActions.narrative}</Paragraph>
            <Box>
              {executiveSummary.recommendedActions.items.map((a, idx) => (
                <Box
                  key={`${a.priority}-${idx}`}
                  sx={{
                    p: 1,
                    mb: 0.75,
                    borderRadius: 1,
                    bgcolor: colors.bg.glass,
                    border: `1px solid ${colors.border.subtle}`,
                    display: 'flex',
                    gap: 1,
                    alignItems: 'flex-start',
                  }}
                >
                  <Chip
                    label={a.priority}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.6rem',
                      fontWeight: 700,
                      bgcolor: `${priorityColor(a.priority)}22`,
                      color: priorityColor(a.priority),
                      border: `1px solid ${priorityColor(a.priority)}55`,
                    }}
                  />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.74rem', lineHeight: 1.5, display: 'block' }}>
                      {a.action}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.62rem' }}>
                      Owner: {a.owner}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
      )}
    </Drawer>
  );
}
