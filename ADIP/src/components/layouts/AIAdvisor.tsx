import { useState } from 'react';
import { Box, Typography, Button, TextField, Chip } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SendIcon from '@mui/icons-material/Send';
import { motion } from 'framer-motion';
import { colors } from '../../theme/colors';
import { layout } from '../../theme/theme';
import { useSimulation } from '../../context/SimulationContext';

export function AIAdvisor() {
  const {
    state,
    querySession,
    askQuestion,
    refreshIntervalMs,
  } = useSimulation();
  const [input, setInput] = useState('');
  const inChatMode = querySession !== null;

  const handleAsk = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    askQuestion(trimmed);
    setInput('');
  };

  const handleSuggestedClick = (q: string) => {
    askQuestion(q);
    setInput('');
  };

  return (
    <Box
      component={motion.aside}
      initial={{ x: 20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      sx={{
        width: layout.aiAdvisorWidth,
        minWidth: layout.aiAdvisorWidth,
        height: '100vh',
        position: 'fixed',
        right: 0,
        top: 0,
        zIndex: 1200,
        background: `linear-gradient(180deg, ${colors.bg.tertiary} 0%, ${colors.bg.primary} 100%)`,
        borderLeft: `1px solid ${colors.border.subtle}`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <Box sx={{ p: 2, borderBottom: `1px solid ${colors.border.subtle}` }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: `linear-gradient(135deg, ${colors.secondary} 0%, ${colors.primary} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 20px ${colors.secondary}44`,
            }}
          >
            <SmartToyIcon sx={{ fontSize: 20, color: '#fff' }} />
          </Box>
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>AI Advisor</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
              Operations Query Console · Live
            </Typography>
          </Box>
        </Box>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', p: 1.5, display: 'flex', flexDirection: 'column' }}>
        {!inChatMode && (
          <>
            <Typography
              variant="caption"
              sx={{
                fontWeight: 700,
                color: colors.secondary,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                fontSize: '0.65rem',
              }}
            >
              Live Executive Insights
            </Typography>
            <Box sx={{ mt: 1, mb: 2 }}>
              {state.dynamicInsights.slice(0, 3).map((insight) => (
                <Box
                  key={insight}
                  sx={{
                    p: 1,
                    mb: 0.5,
                    borderRadius: 1,
                    bgcolor: colors.bg.glass,
                    border: `1px solid ${colors.border.subtle}`,
                    fontSize: '0.72rem',
                    color: colors.text.secondary,
                    lineHeight: 1.45,
                  }}
                >
                  {insight}
                </Box>
              ))}
            </Box>

            <Typography
              variant="caption"
              sx={{
                fontWeight: 700,
                color: colors.text.muted,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                fontSize: '0.65rem',
              }}
            >
              Suggested Questions
            </Typography>
            <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
              {state.aiSuggestedQuestions.map((q) => (
                <Chip
                  key={q}
                  label={q}
                  size="small"
                  onClick={() => handleSuggestedClick(q)}
                  sx={{
                    fontSize: '0.65rem',
                    height: 'auto',
                    py: 0.5,
                    bgcolor: colors.bg.glass,
                    border: `1px solid ${colors.border.subtle}`,
                    cursor: 'pointer',
                    '&:hover': { borderColor: colors.primary, color: colors.primary },
                  }}
                />
              ))}
            </Box>
          </>
        )}

        {querySession && (
          <Box
            key={querySession.question}
            component={motion.div}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              borderRadius: 1.5,
              border: `1px solid ${colors.border.purple}`,
              bgcolor: `${colors.secondary}08`,
              overflow: 'hidden',
            }}
          >
            <Box sx={{ p: 1.5, borderBottom: `1px solid ${colors.border.subtle}`, bgcolor: colors.bg.glass }}>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: colors.primary, fontWeight: 700, textTransform: 'uppercase' }}>
                Your Query
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8125rem', fontWeight: 600, mt: 0.5, lineHeight: 1.4 }}>
                {querySession.question}
              </Typography>
            </Box>
            <Box sx={{ p: 1.5, flex: 1, overflow: 'auto' }}>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: colors.secondary, fontWeight: 700, textTransform: 'uppercase' }}>
                AI Analysis
              </Typography>
              <Typography
                variant="body2"
                component="pre"
                sx={{
                  fontSize: '0.75rem',
                  lineHeight: 1.6,
                  color: colors.text.secondary,
                  mt: 0.75,
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'inherit',
                  m: 0,
                }}
              >
                {querySession.answer}
              </Typography>
            </Box>
          </Box>
        )}

        {!querySession && (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              p: 2,
              textAlign: 'center',
            }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem', lineHeight: 1.5 }}>
              Select a suggested question or enter a query to analyze live operations telemetry.
            </Typography>
          </Box>
        )}
      </Box>

      <Box sx={{ p: 1.5, borderTop: `1px solid ${colors.border.subtle}` }}>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <TextField
            size="small"
            fullWidth
            placeholder="Ask about Payments, releases, incidents..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk(input)}
            sx={{
              '& .MuiOutlinedInput-root': {
                fontSize: '0.75rem',
                bgcolor: colors.bg.glass,
                '& fieldset': { borderColor: colors.border.subtle },
              },
            }}
          />
          <Button
            variant="contained"
            size="small"
            onClick={() => handleAsk(input)}
            sx={{ minWidth: 36, bgcolor: colors.primary }}
          >
            <SendIcon sx={{ fontSize: 16 }} />
          </Button>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem', mt: 0.75, display: 'block', textAlign: 'center' }}>
          Auto-refresh {refreshIntervalMs / 1000}s · Tick #{state.tick}
        </Typography>
      </Box>
    </Box>
  );
}
