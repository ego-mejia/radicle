import { can } from '../../../../lib/permissions';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { columnCategory } from '../../../../lib/boards';
import { filterClauses, type BoardFilters as Filters } from '../../../../lib/rql';
import {
  boardKeys,
  createBoard,
  fetchBoardData,
  fetchBoards,
} from '../../../../services/api/boards';
import { fetchSearchFields, projectKeys } from '../../../../services/api/projects';
import type { Swimlane } from '../../../../services/api/types';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { TicketPanel } from '../../../tickets/components/TicketPanel';
import { BoardColumn } from '../../components/BoardColumn';
import { BoardFilters } from '../../components/BoardFilters';
import { BoardLanes } from '../../components/BoardLanes';
import { BoardToolbar } from '../../components/BoardToolbar';
import { DropResolver } from '../../components/DropResolver';
import { TicketCard } from '../../components/TicketCard';
import { useBoardDrag } from '../../hooks/useBoardDrag';
import { SprintBanner } from '../../../sprints/components/SprintBanner';
import * as S from './style';

export function BoardView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/board' });
  const search = useSearch({ from: '/app/p/$key/board' });
  const navigate = useNavigate({ from: '/p/$key/board' });
  const queryClient = useQueryClient();
  const projectKey = key.toUpperCase();
  const { data: project, isPending: loadingProject, isError } = useProject(projectKey);
  const { t: openKey, board: boardParam, qf, lane, ...filters } = search;
  const quickFilters = qf ? qf.split(',') : [];
  const { data: fields } = useQuery({
    queryKey: projectKeys.fields(projectKey),
    queryFn: () => fetchSearchFields(projectKey),
  });
  const { data: boards } = useQuery({
    queryKey: boardKeys.list(projectKey),
    queryFn: () => fetchBoards(projectKey),
  });
  const boardId = boardParam ?? boards?.[0]?.id;
  const q = filterClauses(filters).join(' AND ');
  const params = { quick_filters: quickFilters, swimlane: lane as Swimlane | undefined, q };
  const dataKey = boardKeys.data(boardId ?? '', params);
  const { data, isPending } = useQuery({
    queryKey: dataKey,
    queryFn: () => fetchBoardData(boardId!, params),
    enabled: Boolean(boardId),
  });
  const dnd = useBoardDrag(data, projectKey, dataKey);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor),
  );
  const create = useMutation({
    mutationFn: () => createBoard(projectKey, { name: t('board.newName') }),
    onSuccess: async (board) => {
      await queryClient.invalidateQueries({ queryKey: boardKeys.list(projectKey) });
      void navigate({ to: '/p/$key/boards/$id', params: { key: projectKey, id: board.id } });
    },
  });

  if (loadingProject) return <PageSpinner />;
  if (isError || !project) return <EmptyState plant="seed" title={t('board.notFound')} />;

  const canDrag = can(project, 'ticket.transition');
  const isAdmin = can(project, 'board.manage');
  const go = (next: Partial<typeof search>) => void navigate({ search: { ...search, ...next } });
  const setFilters = (next: Filters) =>
    void navigate({ search: { ...next, t: openKey, board: boardParam, qf, lane } });

  return (
    <>
      <ProjectHeader project={project} />
      {data && boards && (
        <BoardToolbar
          boards={boards}
          board={data.board}
          activeFilters={quickFilters}
          swimlane={data.swimlane_by}
          isAdmin={isAdmin}
          onBoard={(id) => go({ board: id, qf: undefined, lane: undefined })}
          onFilters={(ids) => go({ qf: ids.length ? ids.join(',') : undefined })}
          onSwimlane={(value) => go({ lane: value })}
          onConfigure={() =>
            void navigate({
              to: '/p/$key/boards/$id',
              params: { key: projectKey, id: data.board.id },
            })
          }
          onCreate={() => create.mutate()}
        />
      )}
      {data?.board.kind === 'scrum' && (
        <SprintBanner project={projectKey} boardId={data.board.id} sprint={data.sprint} />
      )}
      <BoardFilters
        project={project}
        tags={fields?.values?.tags ?? []}
        value={filters}
        onChange={setFilters}
      />
      {!data || isPending ? (
        <PageSpinner />
      ) : (
        <DndContext
          sensors={sensors}
          onDragStart={(e) => void dnd.onDragStart(e)}
          onDragEnd={dnd.onDragEnd}
          onDragCancel={dnd.cancel}
        >
          {data.swimlane_by !== 'none' ? (
            <BoardLanes
              data={data}
              columnState={dnd.columnState}
              canDrag={canDrag}
              onOpen={(ticketKey) => go({ t: ticketKey })}
            />
          ) : (
            <S.Columns
              style={{ gridTemplateColumns: `repeat(${data.columns.length}, minmax(240px, 1fr))` }}
            >
              {data.columns.map((column) => {
                const category = columnCategory(data.board, data.board.columns[column.index]!);
                return (
                  <BoardColumn
                    key={column.index}
                    dropId={`col:${column.index}`}
                    index={column.index}
                    name={column.name}
                    category={category}
                    tickets={column.tickets}
                    count={column.count}
                    wipLimit={column.wip_limit}
                    overLimit={column.over_limit}
                    state={dnd.columnState(column.index)}
                    canDrag={canDrag}
                    onOpen={(ticketKey) => go({ t: ticketKey })}
                    fields={data.board.card_fields}
                    footer={
                      column.done_only && (
                        <Link
                          to="/p/$key/list"
                          params={{ key: projectKey }}
                          search={{
                            q: `project = ${projectKey} AND category = done ORDER BY resolved DESC`,
                          }}
                        >
                          {t('board.seeAllDone', { days: data.board.done_window_days })}
                        </Link>
                      )
                    }
                  />
                );
              })}
            </S.Columns>
          )}
          {/* No drop animation: it flew the card back to where the drag began. */}
          <DragOverlay dropAnimation={null}>
            {dnd.drag && <TicketCard ticket={dnd.drag} fields={data.board.card_fields} overlay />}
          </DragOverlay>
        </DndContext>
      )}
      {dnd.pending && (
        <DropResolver
          ticketKey={dnd.pending.ticket.key}
          ticketType={dnd.pending.ticket.type}
          options={dnd.pending.options}
          onCancel={dnd.closePending}
          onPick={({ option, resolution, comment, fields: values, logMinutes }) =>
            dnd.resolve({
              transition: option.name,
              resolution,
              comment,
              fields: values,
              log_minutes: logMinutes,
            })
          }
        />
      )}
      <TicketPanel ticketKey={openKey} onClose={() => go({ t: undefined })} />
    </>
  );
}
