import { Box } from '@mui/material';
import { colors, riskColors } from '../../theme/colors';

interface Node {
  id: string;
  label: string;
  x: number;
  y: number;
  risk: string;
}

interface DependencyGraphProps {
  nodes: Node[];
  edges: string[][];
  height?: number;
}

export function DependencyGraph({ nodes, edges, height = 220 }: DependencyGraphProps) {
  const getNode = (id: string) => nodes.find((n) => n.id === id);

  return (
    <Box sx={{ position: 'relative', height, width: '100%' }}>
      <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {edges.map(([from, to], i) => {
          const a = getNode(from);
          const b = getNode(to);
          if (!a || !b) return null;
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={colors.border.glow}
              strokeWidth="0.4"
              strokeDasharray="1,1"
              opacity={0.6}
            />
          );
        })}
        {nodes.map((node) => {
          const color = riskColors[node.risk as keyof typeof riskColors] || colors.primary;
          return (
            <g key={node.id} filter="url(#glow)">
              <circle cx={node.x} cy={node.y} r="6" fill={`${color}33`} stroke={color} strokeWidth="0.6" />
              <text
                x={node.x}
                y={node.y + 10}
                textAnchor="middle"
                fill={colors.text.secondary}
                fontSize="3.2"
                fontFamily="Inter, sans-serif"
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </Box>
  );
}
