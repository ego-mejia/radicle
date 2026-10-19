import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Select } from '../../../../components/ui/Input';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { boardKeys, createBoard, fetchBoards } from '../../../../services/api/boards';
import {
  fetchBacklog,
  fetchSprint,
  fetchSprintReport,
  fetchSprints,
  sprintKeys,
} from '../../../../services/api/sprints';
import type { Sprint, TicketSummary } from '../../../../services/api/types';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { TicketPanel } from '../../../tickets/components/TicketPanel';
import { CompleteSprintModal } from '../../components/CompleteSprintModal';
import { SprintSection } from '../../components/SprintSection';
import { StartSprintModal } from '../../components/StartSprintModal';
import { useSprintActions } from '../../hooks/useSprintActions';
import * as S from './style';

/** Scrum planning: open sprints on top, the board's backlog below, drag between them. */
export function BacklogView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/backlog' });
  const search = useSearch({ from: '/app/p/$key/backlog' });
  const navigate = useNavigate({ from: '/p/$key/backlog' });
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const projectKey = key.toUpperCase();
  const { data: project, isPending: loadingProject, isError } = useProject(projectKey);
  const { data: boards } = useQuery({
    queryKey: boardKeys.list(projectKey),
    queryFn: () => fetchBoards(projectKey),
  });
  const scrumBoards = (boards ?? []).filter((b) => b.kind === 'scrum');
  const board = scrumBoards.find((b) => b.id === search.board) ?? scrumBoards[0];
  const boardId = board?.id ?? '';
  const { data: sprints } = useQuery({
    queryKey: sprintKeys.list(boardId),
    queryFn: () => fetchSprints(boardId),
    enabled: Boolean(board),
  });
  const open = (sprints ?? []).filter((s) => s.state !== 'closed');
  const details = useQueries({
    queries: open.map((s) => ({
      queryKey: sprintKeys.detail(s.id),
      queryFn: () => fetchSprint(s.id),
    })),
  });
  const { data: backlog } = useQuery({
    queryKey: sprintKeys.backlog(boardId, {}),
    queryFn: () => fetchBacklog(boardId, {}),
    enabled: Boolean(board),
  });
  const actions = useSprintActions(boardId);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [target, setTarget] = useState('');
  const [starting, setStarting] = useState<Sprint | null>(null);
  const [completing, setCompleting] = useState<Sprint | null>(null);
  const [deleting, setDeleting] = useState<Sprint | null>(null);
  const { data: report } = useQuery({
    queryKey: sprintKeys.report(completing?.id ?? ''),
    queryFn: () => fetchSprintReport(completing!.id),
    enabled: Boolean(completing),
  });
  const newBoard = useMutation({
    mutationFn: () => createBoard(projectKey, { name: 'Scrum', kind: 'scrum' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardKeys.list(projectKey) }),
  });
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor),
  );

  if (loadingProject) return <PageSpinner />;
  if (isError || !project) return <EmptyState plant="seed" title={t('board.notFound')} />;
  const isAdmin = project.role === 'admin' && !project.archived;
  const canEdit = project.role !== 'viewer' && !project.archived;

  if (boards && !board) {
    return (
      <>
        <ProjectHeader project={project} />
        <EmptyState
          plant="seed"
          title={t('sprints.noScrum')}
          text={t('sprints.noScrumHelp')}
          action={
            isAdmin && (
              <Button variant="primary" onClick={() => newBoard.mutate()}>
                {t('sprints.createScrum')}
              </Button>
            )
          }
        />
      </>
    );
  }

  // Where each ticket is now: a sprint id or 'backlog'.
  const where: Record<string, string> = {};
  const lists: { sprint: Sprint; tickets: TicketSummary[] }[] = open.map((s, i) => {
    const tickets = details[i]?.data?.tickets ?? [];
    for (const ticket of tickets) where[ticket.key] = s.id;
    return { sprint: s, tickets };
  });
  for (const ticket of backlog?.items ?? []) where[ticket.key] = 'backlog';
  const hasActive = open.some((s) => s.state === 'active');
  const openTicket = (ticketKey?: string) => void navigate({ search: { ...search, t: ticketKey } });

  const moveTo = (keys: string[], to: string) => {
    const moving = keys.filter((k) => where[k] !== to);
    if (moving.length === 0) return;
    actions.move.mutate(
      { keys: moving, to, from: where },
      { onSuccess: () => setSelected(new Set()) },
    );
  };
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    const to = over?.data.current?.list as string | undefined;
    const ticketKey = active.data.current?.key as string | undefined;
    if (!to || !ticketKey) return;
    moveTo(selected.has(ticketKey) ? [...selected] : [ticketKey], to);
  };
  const select = (ticketKey: string, value: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (value) next.add(ticketKey);
      else next.delete(ticketKey);
      return next;
    });

  return (
    <>
      <ProjectHeader project={project} />
      <S.Bar>
        {scrumBoards.length > 1 && (
          <Select
            aria-label={t('board.board')}
            value={boardId}
            onChange={(e) => void navigate({ search: { board: e.target.value } })}
          >
            {scrumBoards.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        )}
        {selected.size > 0 && (
          <S.Selection role="group" aria-label={t('sprints.selection')}>
            <span>{t('sprints.selected', { count: selected.size })}</span>
            <Select
              aria-label={t('sprints.moveTo')}
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="">{t('sprints.moveTo')}</option>
              {open.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
              <option value="backlog">{t('sprints.backlog')}</option>
            </Select>
            <Button size="sm" disabled={!target} onClick={() => moveTo([...selected], target)}>
              {t('sprints.move')}
            </Button>
          </S.Selection>
        )}
        <S.Spacer />
        {isAdmin && (
          <Button size="sm" onClick={() => actions.create.mutate({})}>
            <Plus />
            {t('sprints.create')}
          </Button>
        )}
      </S.Bar>
      {!sprints || !backlog ? (
        <PageSpinner />
      ) : (
        <DndContext sensors={sensors} onDragEnd={onDragEnd}>
          <S.Lists>
            {lists.map(({ sprint, tickets }) => (
              <SprintSection
                key={sprint.id}
                sprint={sprint}
                tickets={tickets}
                selected={selected}
                canEdit={canEdit}
                isAdmin={isAdmin}
                canStart={!hasActive}
                onSelect={select}
                onOpen={openTicket}
                onStart={() => setStarting(sprint)}
                onComplete={() => setCompleting(sprint)}
                onDelete={() => setDeleting(sprint)}
              />
            ))}
            <SprintSection
              sprint={null}
              tickets={backlog.items}
              total={backlog.total}
              selected={selected}
              canEdit={canEdit}
              isAdmin={isAdmin}
              canStart={false}
              onSelect={select}
              onOpen={openTicket}
            />
          </S.Lists>
        </DndContext>
      )}
      {starting && (
        <StartSprintModal
          sprint={starting}
          pending={actions.start.isPending}
          error={actions.start.error ? errorMessage(actions.start.error) : null}
          onCancel={() => {
            actions.start.reset();
            setStarting(null);
          }}
          onStart={(body) =>
            actions.start.mutate({ id: starting.id, body }, { onSuccess: () => setStarting(null) })
          }
        />
      )}
      {completing && (
        <CompleteSprintModal
          sprint={completing}
          report={report}
          futureSprints={open.filter((s) => s.state === 'future')}
          pending={actions.complete.isPending}
          error={actions.complete.error ? errorMessage(actions.complete.error) : null}
          onCancel={() => {
            actions.complete.reset();
            setCompleting(null);
          }}
          onComplete={(body) =>
            actions.complete.mutate(
              { id: completing.id, body },
              { onSuccess: () => setCompleting(null) },
            )
          }
        />
      )}
      <ConfirmDialog
        open={Boolean(deleting)}
        title={t('sprints.delete', { name: deleting?.name ?? '' })}
        message={t('sprints.deleteConfirm')}
        confirmLabel={t('common.delete')}
        onConfirm={() => {
          if (deleting) actions.remove.mutate(deleting.id);
          setDeleting(null);
        }}
        onCancel={() => setDeleting(null)}
      />
      <TicketPanel ticketKey={search.t} onClose={() => openTicket(undefined)} />
    </>
  );
}
