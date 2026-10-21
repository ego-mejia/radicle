import { useTranslation } from 'react-i18next';
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
import { formatDate } from '../../../../lib/format';
import type { AnalyticsDay } from '../../../../services/api/folioAnalytics';
import * as S from './style';

/** Views per day as bars, and distinct readers as a line (Folio 5.9). */
export function ViewsChart({ days, height = 220 }: { days: AnalyticsDay[]; height?: number }) {
  const { t } = useTranslation();
  const theme = useTheme();
  const rows = days.map((d) => ({ ...d, label: formatDate(d.day) }));
  return (
    <S.Wrap role="img" aria-label={t('folio.analytics.chart', { count: days.length })}>
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid stroke={theme.color.border} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" stroke={theme.color.textMuted} fontSize={11} minTickGap={24} />
          <YAxis stroke={theme.color.textMuted} fontSize={11} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: theme.color.surface, borderColor: theme.color.border }}
            cursor={{ fill: theme.color.surface2 }}
          />
          <Legend />
          <Bar
            dataKey="views"
            name={t('folio.analytics.views')}
            fill={theme.color.accent}
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
          <Line
            dataKey="unique"
            name={t('folio.analytics.readers')}
            stroke={theme.color.textMuted}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </S.Wrap>
  );
}
