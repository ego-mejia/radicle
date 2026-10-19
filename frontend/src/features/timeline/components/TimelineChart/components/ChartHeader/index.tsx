import { useTheme } from 'styled-components';
import type { Tick } from '../../../../../../lib/timeline';

type Props = { ticks: Tick[]; origin: number; px: number; width: number; height: number };

/** Date labels along the top of the chart. */
export function ChartHeader({ ticks, origin, px, width, height }: Props) {
  const theme = useTheme();
  return (
    <svg width={width} height={height} aria-hidden>
      <rect width={width} height={height} fill={theme.color.surface} />
      {ticks.map((tick) => {
        const x = (tick.day - origin) * px;
        return (
          <g key={tick.day}>
            <line x1={x} x2={x} y1={tick.major ? 14 : 24} y2={height} stroke={theme.color.border} />
            <text
              x={x + 4}
              y={height - 10}
              fontSize={11}
              fontWeight={tick.major ? 700 : 400}
              fill={tick.major ? theme.color.text : theme.color.textMuted}
            >
              {tick.label}
            </text>
          </g>
        );
      })}
      <line x1={0} x2={width} y1={height - 0.5} y2={height - 0.5} stroke={theme.color.border} />
    </svg>
  );
}
