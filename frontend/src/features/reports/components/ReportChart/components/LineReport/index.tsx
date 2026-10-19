import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from 'styled-components';
import type { ReportData } from '../../../../../../services/api/types';

type Series = { key: string; label: string; muted?: boolean; dashed?: boolean };

type Props = {
  report: ReportData;
  x: string;
  series: Series[];
  markers?: string;
  height?: number | `${number}%`;
};

/** Lines over time: burndown (ideal vs remaining) and burnup (scope vs completed). */
export function LineReport({ report, x, series, markers, height = 340 }: Props) {
  const theme = useTheme();
  const marked = markers ? report.rows.filter((r) => r[markers]).map((r) => String(r[x])) : [];
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={report.rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid stroke={theme.color.border} strokeDasharray="3 3" />
        <XAxis dataKey={x} stroke={theme.color.textMuted} fontSize={11} />
        <YAxis stroke={theme.color.textMuted} fontSize={11} unit="h" />
        <Tooltip
          contentStyle={{ background: theme.color.surface, borderColor: theme.color.border }}
        />
        <Legend />
        {marked.map((day) => (
          <ReferenceLine key={day} x={day} stroke={theme.color.warning} strokeDasharray="2 4" />
        ))}
        {series.map((s) => (
          <Line
            key={s.key}
            type="linear"
            dataKey={s.key}
            name={s.label}
            stroke={s.muted ? theme.color.textMuted : theme.color.accent}
            strokeWidth={s.muted ? 1.5 : 2.5}
            strokeDasharray={s.dashed ? '6 4' : undefined}
            dot={!s.muted}
            connectNulls={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
