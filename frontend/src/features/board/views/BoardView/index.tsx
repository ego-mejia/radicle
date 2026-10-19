import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import type { BoardFilters as Filters } from '../../../../lib/rql';
import { fetchSearchFields, projectKeys } from '../../../../services/api/projects';
import { fetchTransitions, ticketKeys, transitionTicket } from '../../../../services/api/tickets';
import {
  CATEGORIES,
  type Category,
  type Resolution,
  type TicketSummary,
  type TransitionOption,
} from '../../../../services/api/types';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { TicketPanel } from '../../../tickets/components/TicketPanel';
import { BoardColumn } from '../../components/BoardColumn';
import { BoardFilters } from '../../components/BoardFilters';
import { DropResolver } from '../../components/DropResolver';
import { TicketCard } from '../../components/TicketCard';
import { DONE_WINDOW_DAYS, useBoard } from '../../hooks/useBoard';
import * as S from './style';

type Drag = { ticket: TicketSummary; options: TransitionOption[] | null };
type Pending = { ticket: TicketSummary; options: TransitionOption[] };

export function BoardView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/board' });
  const search = useSearch({ from: '/app/p/$key/board' });
  const navigate = useNavigate({ from: '/p/$key/board' });
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const projectKey = key.toUpperCase();
  const { data: project, isPending: loadingProject, isError } = useProject(projectKey);
  const { t: openKey, ...filters } = search;
  const board = useBoard(projectKey, filters);
  const { data: fields } = useQuery({
    queryKey: projectKeys.fields(projectKey),
    queryFn: () => fetchSearchFields(projectKey),
  });
  const [drag, setDrag] = useState<Drag | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor),
  );

  const move = useMutation({
    mutationFn: (v: {
      key: string;
      to: string;
      resolution: Resolution | null;
      transition: string;
    }) => transitionTicket(v.key, v.to, v.resolution, v.transition),
    onSuccess: (ticket) => {
      for (const w of ticket.warnings ?? []) {
        toast(
          w.code === 'blocked'
            ? t('ticket.warningBlocked', { keys: (w.by ?? []).join(', ') })
            : w.message,
          'warning',
        );
      }
    },
    onError: (error) => toast(errorMessage(error), 'error'),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ticketKeys.all });
      void queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectKey) });
    },
  });

  if (loadingProject) return <PageSpinner />;
  if (isError || !project) return <EmptyState plant="seed" title={t('board.notFound')} />;

  const canDrag = project.role !== 'viewer' && !project.archived;
  const setFilters = (next: Filters) => void navigate({ search: { ...next, t: openKey } });
  const openTicket = (ticketKey?: string) =>
    void navigate({ search: { ...filters, t: ticketKey } });

  const onDragStart = async (event: DragStartEvent) => {
    const ticket = event.active.data.current?.ticket as TicketSummary;
    setDrag({ ticket, options: null });
    const options = await queryClient.fetchQuery({
      queryKey: [...ticketKeys.transitions(ticket.key), 'drag'],
      queryFn: () => fetchTransitions(ticket.key),
      staleTime: 0,
    });
    setDrag((current) => (current?.ticket.key === ticket.key ? { ticket, options } : current));
  };

  const onDragEnd = (event: DragEndEvent) => {
    const current = drag;
    setDrag(null);
    const target = event.over?.id as Category | undefined;
    if (!current || !target || target === current.ticket.status.category || !current.options)
      return;
    const options = current.options.filter((o) => o.category === target);
    if (options.length === 0) return;
    const only = options[0]!;
    const resolutions = only.allowed_resolutions ?? [];
    if (options.length === 1 && (only.category !== 'done' || resolutions.length <= 1)) {
      move.mutate({
        key: current.ticket.key,
        to: only.to_status,
        resolution: resolutions[0] ?? null,
        transition: only.name,
      });
    } else {
      setPending({ ticket: current.ticket, options });
    }
  };

  const columnState = (category: Category): 'idle' | 'allowed' | 'blocked' => {
    if (!drag || category === drag.ticket.status.category) return 'idle';
    if (!drag.options) return 'idle';
    return drag.options.some((o) => o.category === category) ? 'allowed' : 'blocked';
  };

  return (
    <>
      <ProjectHeader project={project} />
      <BoardFilters
        project={project}
        tags={fields?.values?.tags ?? []}
        value={filters}
        onChange={setFilters}
      />
      {board.isPending ? (
        <PageSpinner />
      ) : (
        <DndContext
          sensors={sensors}
          onDragStart={(e) => void onDragStart(e)}
          onDragEnd={onDragEnd}
          onDragCancel={() => setDrag(null)}
        >
          <S.Columns>
            {CATEGORIES.map((category) => (
              <BoardColumn
                key={category}
                category={category}
                tickets={board.columns[category]}
                state={columnState(category)}
                canDrag={canDrag}
                onOpen={openTicket}
                footer={
                  category === 'done' && (
                    <Link
                      to="/p/$key/list"
                      params={{ key: projectKey }}
                      search={{ q: board.allDoneQuery }}
                    >
                      {t('board.seeAllDone', { days: DONE_WINDOW_DAYS })}
                    </Link>
                  )
                }
              />
            ))}
          </S.Columns>
          <DragOverlay>{drag && <TicketCard ticket={drag.ticket} overlay />}</DragOverlay>
        </DndContext>
      )}
      {pending && (
        <DropResolver
          ticketKey={pending.ticket.key}
          options={pending.options}
          onCancel={() => setPending(null)}
          onPick={({ option, resolution }) => {
            move.mutate({
              key: pending.ticket.key,
              to: option.to_status,
              resolution,
              transition: option.name,
            });
            setPending(null);
          }}
        />
      )}
      <TicketPanel ticketKey={openKey} onClose={() => openTicket(undefined)} />
    </>
  );
}
