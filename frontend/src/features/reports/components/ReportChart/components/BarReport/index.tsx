import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from 'styled-components';
import type { ReportData } from '../../../../../../services/api/types';

type Series = { key: string; label: string; muted?: boolean; line?: boolean };

type Props = {
  report: ReportData;
  x: string;
  series: Series[];
  unit?: string;
  horizontal?: boolean;
  height?: number | `${number}%`;
};

/** Bars (and an optional line): velocity, created vs resolved, distribution and time. */
export function BarReport({ report, x, series, unit, horizontal = false, height }: Props) {
  const theme = useTheme();
  const size = height ?? (horizontal ? Math.max(200, report.rows.length * 34 + 60) : 340);
  return (
    <ResponsiveContainer width="100%" height={size}>
      <ComposedChart
        data={report.rows}
        layout={horizontal ? 'vertical' : 'horizontal'}
        margin={{ top: 8, right: 16, bottom: 8, left: horizontal ? 24 : 0 }}
      >
        <CartesianGrid stroke={theme.color.border} strokeDasharray="3 3" />
        {horizontal ? (
          <>
            <XAxis type="number" stroke={theme.color.textMuted} fontSize={11} unit={unit} />
            <YAxis
              type="category"
              dataKey={x}
              stroke={theme.color.textMuted}
              fontSize={11}
              width={120}
            />
          </>
        ) : (
          <>
            <XAxis dataKey={x} stroke={theme.color.textMuted} fontSize={11} />
            <YAxis stroke={theme.color.textMuted} fontSize={11} unit={unit} />
          </>
        )}
        <Tooltip
          contentStyle={{ background: theme.color.surface, borderColor: theme.color.border }}
          cursor={{ fill: theme.color.surface2 }}
        />
        {series.length > 1 && <Legend />}
        {series.map((s) =>
          s.line ? (
            <Line
              key={s.key}
              dataKey={s.key}
              name={s.label}
              stroke={theme.color.warning}
              strokeWidth={2}
              isAnimationActive={false}
            />
          ) : (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.label}
              fill={s.muted ? theme.color.catTodo : theme.color.catDone}
              radius={[3, 3, 0, 0]}
              isAnimationActive={false}
            />
          ),
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
