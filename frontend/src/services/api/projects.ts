import { api, unwrap } from './client';
import type { ProjectRole } from './types';

export const projectKeys = {
  all: ['projects'] as const,
  list: (archived: boolean) => ['projects', 'list', archived] as const,
  detail: (key: string) => ['projects', 'detail', key.toUpperCase()] as const,
  fields: (key?: string) => ['search-fields', key ?? ''] as const,
};

const path = (key: string) => ({ params: { path: { key } } });

export async function fetchProjects(includeArchived = false) {
  return unwrap(
    await api.GET('/api/v1/projects', { params: { query: { include_archived: includeArchived } } }),
  ).items;
}

export async function fetchProject(key: string) {
  return unwrap(await api.GET('/api/v1/projects/{key}', path(key)));
}

export async function createProject(body: {
  key: string;
  name: string;
  description_md?: string;
  template_id?: string | null;
  template_mode?: 'linked' | 'detached';
}) {
  return unwrap(await api.POST('/api/v1/projects', { body }));
}

export async function patchProject(key: string, body: { name?: string; description_md?: string }) {
  return unwrap(await api.PATCH('/api/v1/projects/{key}', { ...path(key), body }));
}

export async function setArchived(key: string, archived: boolean) {
  const url = archived ? '/api/v1/projects/{key}/archive' : '/api/v1/projects/{key}/unarchive';
  return unwrap(await api.POST(url, path(key)));
}

export async function putMember(key: string, handle: string, role: ProjectRole) {
  return unwrap(
    await api.PUT('/api/v1/projects/{key}/members/{handle}', {
      params: { path: { key, handle } },
      body: { role },
    }),
  );
}

export async function removeMember(key: string, handle: string) {
  unwrap(
    await api.DELETE('/api/v1/projects/{key}/members/{handle}', {
      params: { path: { key, handle } },
    }),
  );
}

export async function createArea(key: string, body: { name: string; color?: string | null }) {
  return unwrap(await api.POST('/api/v1/projects/{key}/areas', { ...path(key), body }));
}

export async function patchArea(
  key: string,
  name: string,
  body: { name?: string; color?: string | null; archived?: boolean },
) {
  return unwrap(
    await api.PATCH('/api/v1/projects/{key}/areas/{name}', {
      params: { path: { key, name } },
      body,
    }),
  );
}

export async function createMilestone(
  key: string,
  body: { name: string; target_date?: string | null; description_md?: string },
) {
  return unwrap(await api.POST('/api/v1/projects/{key}/milestones', { ...path(key), body }));
}

export async function patchMilestone(
  key: string,
  name: string,
  body: { name?: string; target_date?: string | null; status?: 'open' | 'closed' },
) {
  return unwrap(
    await api.PATCH('/api/v1/projects/{key}/milestones/{name}', {
      params: { path: { key, name } },
      body,
    }),
  );
}

export async function fetchSearchFields(project?: string) {
  return unwrap(
    await api.GET('/api/v1/search/fields', { params: { query: project ? { project } : {} } }),
  );
}

/** People, agents and groups that are not in the project yet. */
export async function fetchMemberCandidates(key: string, q: string) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/member-candidates', {
      params: { path: { key }, query: { q } },
    }),
  );
}
