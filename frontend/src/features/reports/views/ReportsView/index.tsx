import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { Download } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { rqlValue } from '../../../../lib/rql';
import { boardKeys, fetchBoards } from '../../../../services/api/boards';
import {
  fetchReport,
  type ReportParams,
  reportCsvUrl,
  reportKeys,
} from '../../../../services/api/reports';
import { fetchSprints, sprintKeys } from '../../../../services/api/sprints';
import { REPORT_TYPES, type ReportType } from '../../../../services/api/types';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { DataTable } from '../../components/DataTable';
import { ReportChart } from '../../components/ReportChart';
import { type Filters, ReportFilters } from '../../components/ReportFilters';
import * as S from './style';

const AGILE: ReportType[] = ['burndown', 'burnup', 'velocity', 'cfd', 'control_chart', 'sprint'];
const GENERAL: ReportType[] = ['created_resolved', 'distribution', 'milestone_progress', 'time'];
const SCRUM_ONLY: ReportType[] = ['burndown', 'sprint', 'velocity'];

/** /p/{key}/reports: agile and general reports with filters, chart, data and CSV. */
export function ReportsView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/reports' });
  const search = useSearch({ from: '/app/p/$key/reports' });
  const navigate = useNavigate({ from: '/p/$key/reports' });
  const errorMessage = useErrorMessage();
  const projectKey = key.toUpperCase();
  const type: ReportType = REPORT_TYPES.includes(search.type as ReportType)
    ? (search.type as ReportType)
    : 'burndown';
  const { data: project, isPending, isError } = useProject(projectKey);
  const { data: boards = [] } = useQuery({
    queryKey: boardKeys.list(projectKey),
    queryFn: () => fetchBoards(projectKey),
  });
  const scrum = boards.filter((b) => b.kind === 'scrum');
  const needsScrum = SCRUM_ONLY.includes(type) || (type === 'burnup' && !search.milestone);
  const board = search.board ?? (needsScrum ? scrum[0]?.id : undefined);
  const { data: sprints = [] } = useQuery({
    queryKey: sprintKeys.list(board ?? ''),
    queryFn: () => fetchSprints(board!),
    enabled: Boolean(board) && scrum.some((b) => b.id === board),
  });
  const started = sprints.filter((s) => s.state !== 'future');
  const sprint = search.sprint ?? (started.find((s) => s.state === 'active') ?? started.at(-1))?.id;
  const milestone =
    search.milestone ??
    (type === 'milestone_progress'
      ? (project?.milestones.find((m) => m.status === 'open') ?? project?.milestones[0])?.name
      : undefined);

  const params: ReportParams = {
    project: projectKey,
    board:
      SCRUM_ONLY.includes(type) ||
      ['cfd', 'control_chart', 'created_resolved', 'distribution', 'time'].includes(type)
        ? board
        : undefined,
    sprint: needsScrum && type !== 'velocity' ? sprint : undefined,
    milestone,
    q: search.area ? `area = ${rqlValue(search.area)}` : undefined,
    from: search.from,
    to: search.to,
    field: type === 'distribution' ? (search.field ?? 'area') : undefined,
    interval:
      type === 'created_resolved' ? ((search.interval as 'day' | 'week') ?? 'day') : undefined,
    by: type === 'time' ? ((search.by as ReportParams['by']) ?? 'ticket') : undefined,
  };
  const missing =
    (needsScrum && !board && t('reports.needScrum')) ||
    (needsScrum && type !== 'velocity' && !sprint && t('reports.needSprint')) ||
    (type === 'milestone_progress' && !milestone && t('reports.needMilestone')) ||
    null;
  const report = useQuery({
    queryKey: reportKeys.data(type, params),
    queryFn: () => fetchReport(type, params),
    enabled: !missing,
  });

  if (isPending) return <PageSpinner />;
  if (isError || !project) return <EmptyState plant="seed" title={t('board.notFound')} />;
  const filters: Filters = { ...search, board, sprint, milestone };
  const setFilters = (next: Filters) => void navigate({ search: { type, ...next } });

  return (
    <>
      <ProjectHeader project={project} />
      <S.Layout>
        <S.Nav aria-label={t('reports.title')}>
          {[
            ['agile', AGILE],
            ['general', GENERAL],
          ].map(([group, types]) => (
            <div key={group as string}>
              <h2>{t(`reports.groups.${group}`)}</h2>
              {(types as ReportType[]).map((rt) => (
                <Link
                  key={rt}
                  to="/p/$key/reports"
                  params={{ key: projectKey }}
                  search={{ type: rt }}
                  aria-current={rt === type ? 'page' : undefined}
                >
                  {t(`reports.types.${rt}`)}
                </Link>
              ))}
            </div>
          ))}
        </S.Nav>
        <S.Main>
          <S.Head>
            <div>
              <h1>{t(`reports.types.${type}`)}</h1>
              <p>{t(`reports.help.${type}`)}</p>
            </div>
            {report.data && (
              <S.Csv href={reportCsvUrl(type, params)} download>
                <Download size={16} />
                {t('reports.csv')}
              </S.Csv>
            )}
          </S.Head>
          <ReportFilters
            type={type}
            project={project}
            boards={boards}
            sprints={sprints}
            value={filters}
            onChange={setFilters}
          />
          {missing ? (
            <EmptyState plant="seed" title={missing} />
          ) : report.isPending ? (
            <PageSpinner />
          ) : report.error ? (
            <S.Error role="alert">{errorMessage(report.error)}</S.Error>
          ) : (
            report.data && (
              <>
                <S.Chart data-testid={`report-${type}`}>
                  <ReportChart report={report.data} />
                </S.Chart>
                {report.data.rows.length > 0 ? (
                  <DataTable report={report.data} />
                ) : (
                  <EmptyState plant="pot" title={t('reports.empty')} />
                )}
              </>
            )
          )}
        </S.Main>
      </S.Layout>
    </>
  );
}
