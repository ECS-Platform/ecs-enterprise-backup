import { useEffect, useRef, useState } from 'react';
import {
  Box,
  LinearProgress,
  Typography,
  CircularProgress,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import { GlassCard } from '../common/GlassCard';
import { ModuleHeader } from '../common/ModuleHeader';
import { colors } from '../../theme/colors';
import {
  generateAnalysisResult,
  PHASE_CONFIG,
  type AnalysisPhase,
  type AnalysisResult,
} from '../../data/aiAnalysisMockData';

const PROGRESS_STEPS = [0, 25, 50, 75, 100];
const TOTAL_DURATION_MS = 4000;

interface AIAnalysisWorkflowProps {
  phase: AnalysisPhase;
  inputText: string;
  onComplete?: (result: AnalysisResult) => void;
}

function formatFindingValue(value: string | number | string[]): string {
  if (Array.isArray(value)) return value.join(' · ');
  return String(value);
}

export function AIAnalysisWorkflow({ phase, inputText, onComplete }: AIAnalysisWorkflowProps) {
  const config = PHASE_CONFIG[phase];
  const [progress, setProgress] = useState(0);
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);
  const [currentAgentIndex, setCurrentAgentIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(true);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    const stepDelay = TOTAL_DURATION_MS / (PROGRESS_STEPS.length - 1);

    setProgress(0);
    setCompletedAgents([]);
    setCurrentAgentIndex(0);
    setIsRunning(true);
    setResult(null);

    PROGRESS_STEPS.forEach((step, index) => {
      timers.push(
        setTimeout(() => {
          setProgress(step);

          if (index > 0 && index <= config.agents.length) {
            setCompletedAgents((prev) => [...prev, config.agents[index - 1]]);
          }

          if (index < config.agents.length) {
            setCurrentAgentIndex(index);
          }
        }, stepDelay * index),
      );
    });

    timers.push(
      setTimeout(() => {
        setCompletedAgents(config.agents);
        setCurrentAgentIndex(config.agents.length);
        const analysisResult = generateAnalysisResult(phase, inputText);
        setResult(analysisResult);
        setIsRunning(false);
        onCompleteRef.current?.(analysisResult);
      }, TOTAL_DURATION_MS),
    );

    return () => timers.forEach(clearTimeout);
  }, [phase, inputText, config.agents]);

  const currentAgent = isRunning && currentAgentIndex < config.agents.length
    ? config.agents[currentAgentIndex]
    : null;

  const summaryEntries = result
    ? Object.entries(result).filter(([, value]) => typeof value !== 'object')
    : [];

  const listEntries = result
    ? Object.entries(result).filter(([, value]) => Array.isArray(value))
    : [];

  return (
    <Box sx={{ mt: 1.5 }}>
      <GlassCard sx={{ p: 2 }} glow={config.glow}>
        <ModuleHeader
          title={isRunning ? 'AI Analysis Running' : 'AI Analysis Complete'}
          subtitle={`${phase.charAt(0).toUpperCase() + phase.slice(1)} phase · mock analysis`}
        />

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
          <Box sx={{ flex: 1 }}>
            <LinearProgress
              variant="determinate"
              value={progress}
              sx={{
                height: 8,
                borderRadius: 1,
                bgcolor: colors.bg.glass,
                '& .MuiLinearProgress-bar': {
                  borderRadius: 1,
                  background: `linear-gradient(90deg, ${colors.primary}, ${colors.secondary})`,
                  transition: 'transform 0.35s ease',
                },
              }}
            />
          </Box>
          <Typography variant="caption" sx={{ fontWeight: 700, minWidth: 36, color: colors.primary }}>
            {progress}%
          </Typography>
        </Box>

        <Box
          sx={{
            p: 1.5,
            borderRadius: 1,
            bgcolor: colors.bg.glass,
            border: `1px solid ${colors.border.subtle}`,
            mb: result ? 1.5 : 0,
          }}
        >
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
            Agent Activity Timeline
          </Typography>

          {completedAgents.map((agent) => (
            <Box key={agent} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, py: 0.35 }}>
              <CheckCircleIcon sx={{ fontSize: 14, color: colors.success }} />
              <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>
                {agent}
              </Typography>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: colors.success, ml: 'auto' }}>
                Completed
              </Typography>
            </Box>
          ))}

          {currentAgent && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, py: 0.35 }}>
              <CircularProgress size={14} sx={{ color: colors.secondary }} />
              <Typography variant="caption" sx={{ fontSize: '0.75rem', color: colors.secondary }}>
                {currentAgent}
              </Typography>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: colors.secondary, ml: 'auto' }}>
                Running
              </Typography>
            </Box>
          )}
        </Box>

        {result && (
          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 1.5 }}>
            <Box
              sx={{
                flex: 1,
                p: 1.5,
                borderRadius: 1.5,
                background: `linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(59,130,246,0.08) 100%)`,
                border: `1px solid ${colors.border.purple}`,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1 }}>
                <AutoAwesomeIcon sx={{ fontSize: 16, color: colors.secondary }} />
                <Typography
                  variant="caption"
                  sx={{ fontWeight: 700, color: colors.secondary, textTransform: 'uppercase', letterSpacing: '0.06em' }}
                >
                  AI Findings
                </Typography>
              </Box>
              {summaryEntries.map(([key, value]) => (
                <Box key={key} sx={{ mb: 0.75 }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem', display: 'block' }}>
                    {key}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                    {formatFindingValue(value)}
                  </Typography>
                </Box>
              ))}
            </Box>

            <Box
              sx={{
                flex: 1,
                p: 1.5,
                borderRadius: 1.5,
                bgcolor: colors.bg.glass,
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  fontWeight: 700,
                  color: colors.primary,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  display: 'block',
                  mb: 1,
                }}
              >
                Analysis Summary
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem', display: 'block', mb: 1 }}>
                Analysis for &ldquo;{inputText.trim() || 'unspecified input'}&rdquo; completed across{' '}
                {config.agents.length} agents in {TOTAL_DURATION_MS / 1000}s.
              </Typography>
              {listEntries.map(([key, items]) => (
                <Box key={key} sx={{ mb: 1 }}>
                  <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem', display: 'block', mb: 0.25 }}>
                    {key}
                  </Typography>
                  {(items as string[]).map((item) => (
                    <Typography
                      key={item}
                      variant="caption"
                      color="text.secondary"
                      sx={{ fontSize: '0.72rem', display: 'block', pl: 1, mb: 0.25 }}
                    >
                      • {item}
                    </Typography>
                  ))}
                </Box>
              ))}
              {listEntries.length === 0 && summaryEntries.length > 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.72rem' }}>
                  {summaryEntries.map(([key, value]) => `${key}: ${formatFindingValue(value)}`).join(' · ')}
                </Typography>
              )}
            </Box>
          </Box>
        )}
      </GlassCard>
    </Box>
  );
}
