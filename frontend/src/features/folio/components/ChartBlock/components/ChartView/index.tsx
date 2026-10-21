import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from 'styled-components';
import type { ChartData } from '../../tableData';

export type ChartKind = 'bar' | 'line' | 'area' | 'pie';

type Props = { kind: ChartKind; data: ChartData };

/** Recharts for a chart block; loaded on its own chunk when a page has a chart. */
export default function ChartView({ kind, data }: Props) {
  const theme = useTheme();
  const c = theme.color;
  const palette = [c.accent, c.info, c.violet, c.warning, c.danger, c.catDone, c.textMuted];
  const [header, ...body] = data;
  const series = (header ?? []).slice(1).map(String);
  const rows = body.map((r) =>
    Object.fromEntries([['label', String(r[0])], ...series.map((s, i) => [s, r[i + 1]])]),
  );
  const axes = (
    <>
      <CartesianGrid stroke={c.border} strokeDasharray="3 3" />
      <XAxis dataKey="label" stroke={c.textMuted} fontSize={11} />
      <YAxis stroke={c.textMuted} fontSize={11} />
      <Tooltip contentStyle={{ background: c.surface, borderColor: c.border, color: c.text }} />
      {series.length > 1 ? <Legend /> : null}
    </>
  );

  return (
    <ResponsiveContainer width="100%" height={280}>
      {kind === 'pie' ? (
        <PieChart>
          <Tooltip contentStyle={{ background: c.surface, borderColor: c.border }} />
          <Legend />
          <Pie data={rows} dataKey={series[0]} nameKey="label" outerRadius="80%">
            {rows.map((_, i) => (
              <Cell key={i} fill={palette[i % palette.length]} stroke={c.surface} />
            ))}
          </Pie>
        </PieChart>
      ) : kind === 'line' ? (
        <LineChart data={rows}>
          {axes}
          {series.map((s, i) => (
            <Line key={s} dataKey={s} stroke={palette[i % palette.length]} strokeWidth={2} />
          ))}
        </LineChart>
      ) : kind === 'area' ? (
        <AreaChart data={rows}>
          {axes}
          {series.map((s, i) => (
            <Area
              key={s}
              dataKey={s}
              stroke={palette[i % palette.length]}
              fill={palette[i % palette.length]}
              fillOpacity={0.25}
            />
          ))}
        </AreaChart>
      ) : (
        <BarChart data={rows}>
          {axes}
          {series.map((s, i) => (
            <Bar key={s} dataKey={s} fill={palette[i % palette.length]} />
          ))}
        </BarChart>
      )}
    </ResponsiveContainer>
  );
}
