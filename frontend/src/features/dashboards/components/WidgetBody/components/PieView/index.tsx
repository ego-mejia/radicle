import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { useTheme } from 'styled-components';

type Row = { value: string; count: number };

/** Distribution as a pie; slices cycle through the chart palette. */
export function PieView({ rows }: { rows: Row[] }) {
  const theme = useTheme();
  const palette = [
    theme.color.catDone,
    theme.color.catProgress,
    theme.color.catTodo,
    theme.color.accent,
    theme.color.warning,
    theme.color.textMuted,
  ];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={rows}
          dataKey="count"
          nameKey="value"
          innerRadius="45%"
          outerRadius="80%"
          isAnimationActive={false}
        >
          {rows.map((row, i) => (
            <Cell key={row.value} fill={palette[i % palette.length]} stroke={theme.color.surface} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: theme.color.surface, borderColor: theme.color.border }}
        />
        <Legend formatter={(v) => <span style={{ color: theme.color.text }}>{v}</span>} />
      </PieChart>
    </ResponsiveContainer>
  );
}
