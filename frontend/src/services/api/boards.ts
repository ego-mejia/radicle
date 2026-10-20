import { api, unwrap } from './client';
import type { BoardCard, ColumnConf, Resolution, Swimlane } from './types';

export const boardKeys = {
  list: (project: string) => ['boards', project.toUpperCase()] as const,
  detail: (id: string) => ['boards', 'detail', id] as const,
  // Under the tickets prefix: any ticket change refreshes the boards too.
  data: (id: string, params: object) => ['tickets', 'board', id, params] as const,
};

export async function fetchBoards(project: string) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/boards', { params: { path: { key: project } } }),
  ).items;
}

export async function fetchBoard(id: string) {
  return unwrap(await api.GET('/api/v1/boards/{board_id}', { params: { path: { board_id: id } } }));
}

export async function createBoard(
  project: string,
  body: { name: string; kind?: 'kanban' | 'scrum'; source_rql?: string | null },
) {
  return unwrap(
    await api.POST('/api/v1/projects/{key}/boards', { params: { path: { key: project } }, body }),
  );
}

export type BoardPatch = {
  name?: string;
  kind?: 'kanban' | 'scrum';
  source_rql?: string;
  columns?: ColumnConf[];
  wip_mode?: 'soft' | 'hard';
  swimlane_by?: Swimlane;
  card_fields?: string[];
  done_window_days?: number;
};

export async function patchBoard(id: string, body: BoardPatch) {
  return unwrap(
    await api.PATCH('/api/v1/boards/{board_id}', { params: { path: { board_id: id } }, body }),
  );
}

export async function deleteBoard(id: string) {
  unwrap(await api.DELETE('/api/v1/boards/{board_id}', { params: { path: { board_id: id } } }));
}

export async function fetchBoardData(
  id: string,
  params: { quick_filters?: string[]; swimlane?: Swimlane; q?: string },
) {
  return unwrap(
    await api.GET('/api/v1/boards/{board_id}/data', {
      params: {
        path: { board_id: id },
        query: {
          quick_filters: params.quick_filters?.length ? params.quick_filters : undefined,
          swimlane: params.swimlane,
          q: params.q || undefined,
        },
      },
    }),
  );
}

export type CardMove = {
  ticket: string;
  column: number;
  before?: string | null;
  after?: string | null;
  transition?: string | null;
  resolution?: Resolution | null;
  comment?: string | null;
  fields?: Record<string, unknown> | null;
  log_minutes?: number | null;
  force?: boolean;
};

export async function moveCard(id: string, body: CardMove) {
  return unwrap(
    await api.POST('/api/v1/boards/{board_id}/move', { params: { path: { board_id: id } }, body }),
  );
}

export async function saveQuickFilter(
  boardId: string,
  body: { name: string; rql: string },
  filterId?: string,
) {
  return filterId
    ? unwrap(
        await api.PATCH('/api/v1/boards/{board_id}/quick-filters/{filter_id}', {
          params: { path: { board_id: boardId, filter_id: filterId } },
          body,
        }),
      )
    : unwrap(
        await api.POST('/api/v1/boards/{board_id}/quick-filters', {
          params: { path: { board_id: boardId } },
          body,
        }),
      );
}

export async function deleteQuickFilter(boardId: string, filterId: string) {
  unwrap(
    await api.DELETE('/api/v1/boards/{board_id}/quick-filters/{filter_id}', {
      params: { path: { board_id: boardId, filter_id: filterId } },
    }),
  );
}

export type { BoardCard };
