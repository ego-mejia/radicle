import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { MarkdownView } from '../../../../components/Markdown/MarkdownView';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { dashboardKeys, fetchWidgetData } from '../../../../services/api/dashboards';
import type { ReportData, Widget } from '../../../../services/api/types';
import { BarReport } from '../../../reports/components/ReportChart/components/BarReport';
import { FlowReport } from '../../../reports/components/ReportChart/components/FlowReport';
import { LineReport } from '../../../reports/components/ReportChart/components/LineReport';
import { PieView } from './components/PieView';
import { ProgressView } from './components/ProgressView';
import { TicketList } from './components/TicketList';
import * as S from './style';

const asReport = (data: Record<string, unknown>): ReportData => ({
  type: '',
  title: '',
  columns: [],
  rows: (data.rows as Record<string, unknown>[]) ?? [],
  summary: (data.summary as Record<string, unknown>) ?? {},
});

/** A widget's content, fetched with the viewer's permissions and refreshed every 5 minutes. */
export function WidgetBody({ widget, refreshSeconds }: { widget: Widget; refreshSeconds: number }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const { data, error, isPending } = useQuery({
    queryKey: dashboardKeys.widget(widget.id),
    queryFn: () => fetchWidgetData(widget.id),
    refetchInterval: refreshSeconds * 1000,
  });
  if (isPending) return <PageSpinner />;
  if (error) return <S.Error role="alert">{errorMessage(error)}</S.Error>;
  const d = data.data;
  switch (widget.widget_type) {
    case 'count':
      return (
        <S.Count>
          <strong data-testid={`count-${widget.id}`}>{String(d.count)}</strong>
          {typeof d.label === 'string' && d.label && <span>{d.label}</span>}
        </S.Count>
      );
    case 'markdown':
      return (
        <S.Scroll>
          <MarkdownView readOnly>{String(d.text ?? '')}</MarkdownView>
        </S.Scroll>
      );
    case 'filter_results':
    case 'my_tickets':
    case 'blocked_tickets':
      return (
        <TicketList
          tickets={data.tickets ?? []}
          total={data.total ?? 0}
          showBlockers={widget.widget_type === 'blocked_tickets'}
        />
      );
    case 'distribution': {
      const rows = (d.rows as { value: string; count: number }[]) ?? [];
      if (rows.length === 0) return <S.Empty>{t('dashboards.noTickets')}</S.Empty>;
      return d.chart === 'pie' ? (
        <PieView rows={rows} />
      ) : (
        <BarReport
          report={asReport(d)}
          x="value"
          horizontal
          height="100%"
          series={[{ key: 'count', label: t('reports.cols.count') }]}
        />
      );
    }
    case 'milestone_progress':
      return <ProgressView summary={d.summary as Parameters<typeof ProgressView>[0]['summary']} />;
    case 'created_vs_resolved':
      return (
        <BarReport
          report={asReport(d)}
          x="period"
          height="100%"
          series={[
            { key: 'created', label: t('reports.cols.created'), muted: true },
            { key: 'resolved', label: t('reports.cols.resolved') },
          ]}
        />
      );
    case 'sprint_burndown':
      if (!d.sprint) return <S.Empty>{t('sprints.noActive')}</S.Empty>;
      return (
        <LineReport
          report={asReport(d)}
          x="date"
          markers="scope_change"
          height="100%"
          series={[
            { key: 'ideal_hours', label: t('reports.cols.ideal_hours'), muted: true, dashed: true },
            { key: 'remaining_hours', label: t('reports.cols.remaining_hours') },
          ]}
        />
      );
    case 'cumulative_flow':
      return <FlowReport report={asReport(d)} height="100%" />;
    default:
      return null;
  }
}
