// Folio's day-to-day calls (Folio 2.4): Mis tareas and sharing a page.

import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type FolioTask = S['FolioTaskOut'];
export type TaskStatus = 'open' | 'done' | 'all';
export type ShareIn = S['ShareIn'];
export type ShareResult = S['ShareOut'];

export const taskKeys = {
  all: ['folio', 'tasks'] as const,
  list: (status: TaskStatus) => ['folio', 'tasks', status] as const,
};

export async function fetchMyTasks(status: TaskStatus = 'open'): Promise<FolioTask[]> {
  return unwrap(await api.GET('/api/v1/folio/me/tasks', { params: { query: { status } } })).items;
}

export async function setTaskDone(id: string, done: boolean): Promise<FolioTask> {
  return unwrap(
    await api.PATCH('/api/v1/folio/action-items/{item_id}', {
      params: { path: { item_id: id } },
      body: { done },
    }),
  );
}

export async function shareNode(id: string, body: ShareIn): Promise<ShareResult> {
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/share', {
      params: { path: { node_id: id } },
      body,
    }),
  );
}
