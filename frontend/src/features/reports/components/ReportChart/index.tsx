import type { TFunction } from 'i18next';
import { useTranslation } from 'react-i18next';
import { formatDate } from '../../../../lib/format';
import type { ReportData } from '../../../../services/api/types';
import { BarReport } from './components/BarReport';
import { ControlReport } from './components/ControlReport';
import { FlowReport } from './components/FlowReport';
import { LineReport } from './components/LineReport';
import { type Card, SummaryCards } from './components/SummaryCards';

const num = (v: unknown, unit = '') => (v == null ? '—' : `${v}${unit}`);

/** The chart that fits each report, plus its key numbers. */
export function ReportChart({ report }: { report: ReportData }) {
  const { t } = useTranslation();
  const s = report.summary;
  const col = (key: string) => t(`reports.cols.${key}`);
  switch (report.type) {
    case 'burndown':
      return (
        <>
          <SummaryCards
            cards={[
              { label: col('committed_hours'), value: num(s.committed_hours, 'h') },
              { label: col('remaining_hours'), value: num(s.remaining_hours, 'h'), tone: 'accent' },
              { label: t('reports.workingDays'), value: num(s.working_days) },
            ]}
          />
          <LineReport
            report={report}
            x="date"
            markers="scope_change"
            series={[
              { key: 'ideal_hours', label: col('ideal_hours'), muted: true, dashed: true },
              { key: 'remaining_hours', label: col('remaining_hours') },
            ]}
          />
        </>
      );
    case 'burnup':
      return (
        <LineReport
          report={report}
          x="date"
          series={[
            { key: 'scope_hours', label: col('scope_hours'), muted: true },
            { key: 'completed_hours', label: col('completed_hours') },
          ]}
        />
      );
    case 'velocity':
      return (
        <>
          <SummaryCards
            cards={[
              { label: t('reports.averageLast3'), value: num(s.average_completed_hours, 'h') },
            ]}
          />
          <BarReport
            report={report}
            x="sprint"
            unit="h"
            series={[
              { key: 'committed_hours', label: col('committed_hours'), muted: true },
              { key: 'completed_hours', label: col('completed_hours') },
            ]}
          />
        </>
      );
    case 'cfd':
      return <FlowReport report={report} />;
    case 'control_chart':
      return (
        <>
          <SummaryCards
            cards={[
              { label: t('reports.tickets'), value: num(s.tickets) },
              { label: 'P50', value: num(s.p50_days, ' d') },
              { label: 'P85', value: num(s.p85_days, ' d') },
              { label: 'P95', value: num(s.p95_days, ' d') },
            ]}
          />
          <ControlReport report={report} />
        </>
      );
    case 'created_resolved':
      return (
        <BarReport
          report={report}
          x="period"
          series={[
            { key: 'created', label: col('created'), muted: true },
            { key: 'resolved', label: col('resolved') },
            { key: 'cumulative_difference', label: col('cumulative_difference'), line: true },
          ]}
        />
      );
    case 'distribution':
      return (
        <BarReport
          report={report}
          x="value"
          horizontal
          series={[{ key: 'count', label: col('count') }]}
        />
      );
    case 'time':
      return (
        <BarReport
          report={report}
          x={report.columns[0]!}
          unit="h"
          horizontal
          series={[
            { key: 'original_estimate_hours', label: col('original_estimate_hours'), muted: true },
            { key: 'spent_hours', label: col('spent_hours') },
          ]}
        />
      );
    case 'milestone_progress':
      return <SummaryCards cards={progressCards(s, t)} />;
    case 'sprint': {
      const counts = (s.counts ?? {}) as Record<string, number>;
      return (
        <SummaryCards
          cards={[
            { label: col('committed_hours'), value: num(s.committed_hours, 'h') },
            { label: col('completed_hours'), value: num(s.completed_hours, 'h'), tone: 'accent' },
            ...(['completed', 'not_completed', 'added_after_start', 'removed'] as const).map(
              (k) => ({ label: t(`reports.outcomes.${k}`), value: num(counts[k]) }),
            ),
            {
              label: t('reports.goalMet'),
              value: s.goal_met == null ? '—' : s.goal_met ? t('common.yes') : t('common.no'),
            },
          ]}
        />
      );
    }
    default:
      return null;
  }
}

function progressCards(s: Record<string, unknown>, t: TFunction): Card[] {
  const state = String(s.state);
  return [
    { label: t('reports.progressCount'), value: num(s.percent_by_count, '%') },
    { label: t('reports.progressHours'), value: num(s.percent_by_hours, '%'), tone: 'accent' },
    { label: t('reports.cols.remaining_hours'), value: num(s.remaining_hours, 'h') },
    {
      label: t('reports.pace'),
      value: `${num(s.throughput_hours_per_week)} ${t('reports.hoursPerWeek')}`,
    },
    { label: t('reports.target'), value: s.target_date ? formatDate(String(s.target_date)) : '—' },
    {
      label: t('reports.forecast'),
      value: s.forecast_date ? formatDate(String(s.forecast_date)) : '—',
      tone: state === 'at_risk' ? 'warning' : undefined,
    },
    {
      label: t('reports.state'),
      value: t(`reports.states.${state}`),
      tone: state === 'at_risk' ? 'warning' : state === 'on_track' ? 'accent' : undefined,
    },
  ];
}
