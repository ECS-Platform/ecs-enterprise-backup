import { useState } from 'react';
import { Box, Button, TextField } from '@mui/material';
import { GlassCard } from '../common/GlassCard';
import { ModuleHeader } from '../common/ModuleHeader';
import { AIAnalysisWorkflow } from './AIAnalysisWorkflow';
import { colors } from '../../theme/colors';
import type { AnalysisPhase } from '../../data/aiAnalysisMockData';


interface AnalyzeWithAIPanelProps {
  phase: AnalysisPhase;
  title: string;
  subtitle?: string;
  placeholder: string;
  glow?: 'blue' | 'purple' | 'green' | 'none';
  number?: number;
}

export function AnalyzeWithAIPanel({
  phase,
  title,
  subtitle,
  placeholder,
  glow = 'purple',
  number,
}: AnalyzeWithAIPanelProps) {
  const [inputText, setInputText] = useState('');
  const [analysisKey, setAnalysisKey] = useState(0);
  const [showAnalysis, setShowAnalysis] = useState(false);

 const handleAnalyze = () => {

  setShowAnalysis(true);
  setAnalysisKey((k) => k + 1);
};

  return (
    
    <>
      <GlassCard sx={{ p: 2, mb: 1.5 }} glow={glow}>
        <ModuleHeader number={number} title={title} subtitle={subtitle} />
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <TextField
            fullWidth
            multiline
            rows={2}
            placeholder={placeholder}
            size="small"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            sx={{ '& .MuiOutlinedInput-root': { bgcolor: colors.bg.glass, fontSize: '0.8125rem' } }}
          />
          <Button
            variant="contained"
            onClick={handleAnalyze}
            sx={{ minWidth: 140, bgcolor: colors.secondary, alignSelf: 'flex-start' }}
          >
            Analyze with AI  
          </Button>
        </Box>
      </GlassCard>

{showAnalysis && (
  <AIAnalysisWorkflow
    key={analysisKey}
    phase={phase}
    inputText={inputText}
  />
)}
    </>
  );
}
