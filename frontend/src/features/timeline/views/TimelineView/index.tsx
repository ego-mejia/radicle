import { can } from '../../../../lib/permissions';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Select } from '../../../../components/ui/Input';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { isApiError } from '../../../../services/api/client';
import { isoPlus } from '../../../../lib/sprints';
import { toDay, toIso, type Zoom, ZOOMS } from '../../../../lib/timeline';
import { fetchSearchFields, projectKeys } from '../../../../services/api/projects';
import { patchTicket, ticketKeys } from '../../../../services/api/tickets';
import { fetchTimeline, timelineKeys } from '../../../../services/api/timeline';
import type { TimelineTicket } from '../../../../services/api/types';
import { RqlBar } from '../../../list/components/RqlBar';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { useAreaLook } from '../../../projects/hooks/useAreaLook';
import { TicketPanel } from '../../../tickets/components/TicketPanel';
import { TimelineChart } from '../../components/TimelineChart';
import { UndatedPanel } from '../../components/UndatedPanel';
import * as S from './style';

type Dates = { start_date: string | null; due_date: string | null };

/** Gantt of the project: milestones with forecast, tickets by dates, Blocks arrows. */
export function TimelineView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/timeline' });
  const search = useSearch({ from: '/app/p/$key/timeline' });
  const navigate = useNavigate({ from: '/p/$key/timeline' });
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const projectKey = key.toUpperCase();
  const zoom: Zoom = ZOOMS.includes(search.zoom as Zoom) ? (search.zoom as Zoom) : 'month';
  const groupBy = search.group === 'area' ? 'area' : 'milestone';
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const { data: project, isPending: loadingProject, isError } = useProject(projectKey);
  const areas = useAreaLook(projectKey);
  const { data: fields } = useQuery({
    queryKey: projectKeys.fields(projectKey),
    queryFn: () => fetchSearchFields(projectKey),
  });
  const params = { group_by: groupBy, q: search.q } as const;
  const timeline = useQuery({
    queryKey: timelineKeys.data(projectKey, params),
    queryFn: () => fetchTimeline(projectKey, params),
  });
  const save = useMutation({
    mutationFn: (v: { ticket: TimelineTicket; dates: Dates }) =>
      patchTicket(v.ticket.key, v.ticket.version, v.dates),
    onError: (error) => toast(errorMessage(error), 'error'),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ticketKeys.all }),
  });

  if (loadingProject) return <PageSpinner />;
  if (isError || !project) return <EmptyState plant="seed" title={t('board.notFound')} />;
  const canEdit = can(project, 'ticket.edit');
  const go = (next: Partial<typeof search>) => void navigate({ search: { ...search, ...next } });
  const error =
    isApiError(timeline.error, 422) && timeline.error.problem.position !== undefined
      ? { message: timeline.error.message, position: timeline.error.problem.position }
      : null;
  const data = timeline.data;
  const findUndated = (ticketKey: string) => data?.undated.find((u) => u.key === ticketKey);

  return (
    <>
      <ProjectHeader project={project} />
      <RqlBar
        value={search.q ?? ''}
        onSubmit={(q) => go({ q: q || undefined })}
        fields={fields}
        error={error}
      />
      <S.Toolbar>
        <Select
          aria-label={t('timeline.groupBy')}
          value={groupBy}
          onChange={(e) => go({ group: e.target.value })}
        >
          <option value="milestone">{t('timeline.byMilestone')}</option>
          <option value="area">{t('timeline.byArea')}</option>
        </Select>
        <S.Zoom role="group" aria-label={t('timeline.zoom')}>
          {ZOOMS.map((z) => (
            <button key={z} type="button" aria-pressed={zoom === z} onClick={() => go({ zoom: z })}>
              {t(`timeline.zooms.${z}`)}
            </button>
          ))}
        </S.Zoom>
        {data?.truncated && <S.Warning>{t('timeline.truncated')}</S.Warning>}
      </S.Toolbar>
      {!data ? (
        error ? null : (
          <PageSpinner />
        )
      ) : (
        <S.Body>
          <TimelineChart
            data={data}
            areas={areas}
            zoom={zoom}
            today={isoPlus(0)}
            canEdit={canEdit}
            collapsed={collapsed}
            onToggle={(group) =>
              setCollapsed((prev) => {
                const next = new Set(prev);
                if (next.has(group)) next.delete(group);
                else next.add(group);
                return next;
              })
            }
            onOpen={(ticketKey) => go({ t: ticketKey })}
            onChange={(ticket, dates) => save.mutate({ ticket, dates })}
            onDropUndated={(ticketKey, day) => {
              const ticket = findUndated(ticketKey);
              if (!ticket) return;
              const due = toIso(toDay(day) + 2);
              save.mutate({ ticket, dates: { start_date: day, due_date: due } });
            }}
          />
          <UndatedPanel tickets={data.undated} canEdit={canEdit} onOpen={(k) => go({ t: k })} />
        </S.Body>
      )}
      <TicketPanel ticketKey={search.t} onClose={() => go({ t: undefined })} />
    </>
  );
}
