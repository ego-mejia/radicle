import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from 'styled-components';
import { categoryToken } from '../../../../../../lib/timeline';
import type { Category, ReportData } from '../../../../../../services/api/types';

type Status = { name: string; category: Category };

/** Cumulative flow: one stacked area per status, done at the bottom, in category colors. */
export function FlowReport({
  report,
  height = 360,
}: {
  report: ReportData;
  height?: number | `${number}%`;
}) {
  const theme = useTheme();
  const statuses = ((report.summary.statuses as Status[] | undefined) ?? []).slice().reverse();
  // Several statuses share a category: vary the opacity so the bands stay apart.
  const seen: Record<string, number> = {};
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={report.rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
        <CartesianGrid stroke={theme.color.border} strokeDasharray="3 3" />
        <XAxis dataKey="date" stroke={theme.color.textMuted} fontSize={11} />
        <YAxis stroke={theme.color.textMuted} fontSize={11} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: theme.color.surface, borderColor: theme.color.border }}
        />
        <Legend formatter={(value) => <span style={{ color: theme.color.text }}>{value}</span>} />
        {statuses.map((s) => {
          const n = (seen[s.category] = (seen[s.category] ?? 0) + 1);
          const color = theme.color[categoryToken(s.category)];
          return (
            <Area
              key={s.name}
              type="monotone"
              dataKey={s.name}
              stackId="flow"
              stroke={color}
              fill={color}
              fillOpacity={Math.max(0.35, 0.95 - (n - 1) * 0.2)}
              isAnimationActive={false}
            />
          );
        })}
      </AreaChart>
    </ResponsiveContainer>
  );
}
