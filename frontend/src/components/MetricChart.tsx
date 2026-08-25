import React from 'react';

interface MetricChartProps {
  title: string;
  data: { time: number; value: number; threshold?: number }[];
  unit: string;
  color: 'cyan' | 'crimson' | 'emerald' | 'amber';
  height?: number;
}

export const MetricChart: React.FC<MetricChartProps> = ({
  title,
  data,
  unit,
  color,
  height = 120,
}) => {
  if (!data || data.length === 0) return null;

  const width = 450;
  const padding = { top: 15, right: 15, bottom: 25, left: 35 };
  const graphWidth = width - padding.left - padding.right;
  const graphHeight = height - padding.top - padding.bottom;

  const minVal = Math.min(0, ...data.map((d) => d.value));
  const maxVal = Math.max(...data.map((d) => d.value), ...data.map((d) => d.threshold || 0)) * 1.15 || 10;

  const mapX = (idx: number) => padding.left + (idx / (data.length - 1)) * graphWidth;
  const mapY = (val: number) => padding.top + graphHeight - ((val - minVal) / (maxVal - minVal)) * graphHeight;

  const pointsString = data.map((d, idx) => `${mapX(idx)},${mapY(d.value)}`).join(' ');
  const areaString = `${pointsString} ${mapX(data.length - 1)},${mapY(minVal)} ${mapX(0)},${mapY(minVal)}`;

  const strokeColors = {
    cyan: '#06b6d4',
    crimson: '#ef4444',
    emerald: '#10b981',
    amber: '#f59e0b',
  };

  const fillGradients = {
    cyan: 'rgba(6, 182, 212, 0.2)',
    crimson: 'rgba(239, 68, 68, 0.25)',
    emerald: 'rgba(16, 185, 129, 0.2)',
    amber: 'rgba(245, 158, 11, 0.2)',
  };

  const currentVal = data[data.length - 1]?.value ?? 0;

  return (
    <div className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3">
      <div className="flex items-center justify-between mb-1.5 text-xs font-mono">
        <span className="text-slate-300 font-semibold">{title}</span>
        <span className="font-bold" style={{ color: strokeColors[color] }}>
          {currentVal.toFixed(2)} {unit}
        </span>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
        {/* Y Axis Gridlines */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={width - padding.right}
          y2={padding.top}
          stroke="#1e293b"
          strokeDasharray="2,2"
        />
        <line
          x1={padding.left}
          y1={padding.top + graphHeight / 2}
          x2={width - padding.right}
          y2={padding.top + graphHeight / 2}
          stroke="#1e293b"
          strokeDasharray="2,2"
        />
        <line
          x1={padding.left}
          y1={padding.top + graphHeight}
          x2={width - padding.right}
          y2={padding.top + graphHeight}
          stroke="#334155"
        />

        {/* Shaded Area */}
        <polygon points={areaString} fill={fillGradients[color]} />

        {/* Line Plot */}
        <polyline
          fill="none"
          stroke={strokeColors[color]}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={pointsString}
        />

        {/* Current Point Dot */}
        <circle
          cx={mapX(data.length - 1)}
          cy={mapY(currentVal)}
          r="4"
          fill={strokeColors[color]}
          stroke="#0f172a"
          strokeWidth="2"
        />

        {/* Axis Labels */}
        <text x={padding.left - 5} y={padding.top + 8} textAnchor="end" fill="#64748b" fontSize="9" fontFamily="monospace">
          {maxVal.toFixed(1)}
        </text>
        <text x={padding.left - 5} y={padding.top + graphHeight} textAnchor="end" fill="#64748b" fontSize="9" fontFamily="monospace">
          {minVal.toFixed(0)}
        </text>
        <text x={padding.left} y={height - 8} fill="#64748b" fontSize="9" fontFamily="monospace">
          t=0s
        </text>
        <text x={width - padding.right} y={height - 8} textAnchor="end" fill="#64748b" fontSize="9" fontFamily="monospace">
          t=30s
        </text>
      </svg>
    </div>
  );
};
