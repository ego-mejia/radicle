import { api, unwrap } from './client';
import type { SprintState } from './types';

export const sprintKeys = {
  // Under the tickets prefix: any ticket change refreshes sprints and the backlog.
  list: (board: string) => ['tickets', 'sprints', board] as const,
  detail: (id: string) => ['tickets', 'sprint', id] as const,
  backlog: (board: string, params: object) => ['tickets', 'backlog', board, params] as const,
  report: (id: string) => ['tickets', 'sprint-report', id] as const,
};

export async function fetchSprints(board: string, state?: SprintState) {
  return unwrap(
    await api.GET('/api/v1/boards/{board_id}/sprints', {
      params: { path: { board_id: board }, query: { state } },
    }),
  ).items;
}

export async function fetchSprint(id: string) {
  return unwrap(
    await api.GET('/api/v1/sprints/{sprint_id}', { params: { path: { sprint_id: id } } }),
  );
}

export async function fetchBacklog(
  board: string,
  params: { q?: string; quick_filters?: string[] },
) {
  return unwrap(
    await api.GET('/api/v1/boards/{board_id}/backlog', {
      params: {
        path: { board_id: board },
        query: {
          q: params.q || undefined,
          quick_filters: params.quick_filters?.length ? params.quick_filters : undefined,
        },
      },
    }),
  );
}

export type SprintFields = {
  name?: string | null;
  goal?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  capacity_hours?: number | null;
};

export async function createSprint(board: string, body: SprintFields) {
  return unwrap(
    await api.POST('/api/v1/boards/{board_id}/sprints', {
      params: { path: { board_id: board } },
      body,
    }),
  );
}

export async function patchSprint(
  id: string,
  body: SprintFields & { position?: number; goal_met?: boolean },
) {
  return unwrap(
    await api.PATCH('/api/v1/sprints/{sprint_id}', { params: { path: { sprint_id: id } }, body }),
  );
}

export async function deleteSprint(id: string) {
  unwrap(await api.DELETE('/api/v1/sprints/{sprint_id}', { params: { path: { sprint_id: id } } }));
}

export async function startSprint(id: string, body: SprintFields) {
  return unwrap(
    await api.POST('/api/v1/sprints/{sprint_id}/start', {
      params: { path: { sprint_id: id } },
      body,
    }),
  );
}

export async function completeSprint(
  id: string,
  body: { move_unfinished_to: string; tag_backlog: boolean },
) {
  return unwrap(
    await api.POST('/api/v1/sprints/{sprint_id}/complete', {
      params: { path: { sprint_id: id } },
      body,
    }),
  );
}

export async function addToSprint(id: string, keys: string[]) {
  return unwrap(
    await api.POST('/api/v1/sprints/{sprint_id}/tickets', {
      params: { path: { sprint_id: id } },
      body: { keys },
    }),
  );
}

export async function removeFromSprint(id: string, keys: string[]) {
  return unwrap(
    await api.DELETE('/api/v1/sprints/{sprint_id}/tickets', {
      params: { path: { sprint_id: id } },
      body: { keys },
    }),
  );
}

export async function fetchSprintReport(id: string) {
  return unwrap(
    await api.GET('/api/v1/sprints/{sprint_id}/report', { params: { path: { sprint_id: id } } }),
  );
}
