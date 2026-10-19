import { api, unwrap } from './client';
import type { Preferences } from './types';

export const workKeys = {
  filters: (project?: string) => ['filters', project ?? ''] as const,
  preferences: ['preferences'] as const,
};

export async function fetchFilters(project?: string) {
  return unwrap(await api.GET('/api/v1/filters', { params: { query: project ? { project } : {} } }))
    .items;
}

export async function createFilter(body: {
  name: string;
  rql: string;
  visibility: 'private' | 'project' | 'instance';
  project?: string | null;
}) {
  return unwrap(await api.POST('/api/v1/filters', { body }));
}

export async function deleteFilter(id: string) {
  unwrap(await api.DELETE('/api/v1/filters/{filter_id}', { params: { path: { filter_id: id } } }));
}

export async function rankTicket(key: string, body: { before?: string; after?: string }) {
  return unwrap(await api.POST('/api/v1/tickets/{key}/rank', { params: { path: { key } }, body }));
}

export async function fetchPreferences() {
  return unwrap(await api.GET('/api/v1/me/preferences'));
}

export async function patchPreferences(body: Partial<Preferences>) {
  return unwrap(
    await api.PATCH('/api/v1/me/preferences', { body: body as Record<string, unknown> }),
  );
}
