import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'styled-components';
import type { ReportData } from '../../../../../../services/api/types';

/** Cycle time per resolved ticket, rolling mean and the 50/85/95 percentiles. */
export function ControlReport({ report }: { report: ReportData }) {
  const { t } = useTranslation();
  const theme = useTheme();
  const rows = report.rows
    .filter((r) => r.cycle_days != null)
    .map((r) => ({ ...r, day: String(r.resolved).slice(0, 10) }));
  const lines = [
    ['p50_days', 'P50'],
    ['p85_days', 'P85'],
    ['p95_days', 'P95'],
  ] as const;
  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={rows} margin={{ top: 8, right: 40, bottom: 8, left: 0 }}>
        <CartesianGrid stroke={theme.color.border} strokeDasharray="3 3" />
        <XAxis dataKey="day" stroke={theme.color.textMuted} fontSize={11} />
        <YAxis stroke={theme.color.textMuted} fontSize={11} unit={t('reports.daysUnit')} />
        <Tooltip
          contentStyle={{ background: theme.color.surface, borderColor: theme.color.border }}
        />
        {lines.map(([key, label]) =>
          report.summary[key] != null ? (
            <ReferenceLine
              key={key}
              y={Number(report.summary[key])}
              stroke={theme.color.textMuted}
              strokeDasharray="4 4"
              label={{ value: label, position: 'right', fill: theme.color.textMuted, fontSize: 11 }}
            />
          ) : null,
        )}
        <Scatter
          dataKey="cycle_days"
          name={t('reports.cols.cycle_days')}
          fill={theme.color.accent}
        />
        <Line
          dataKey="rolling_mean_days"
          name={t('reports.cols.rolling_mean_days')}
          stroke={theme.color.warning}
          dot={false}
          strokeWidth={2}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
