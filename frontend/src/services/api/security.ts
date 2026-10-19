import { api, unwrap } from './client';

export const securityKeys = {
  levels: (key: string) => ['security-levels', key.toUpperCase()] as const,
};

export async function fetchLevels(key: string) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/security-levels', { params: { path: { key } } }),
  ).items;
}

export async function createLevel(
  key: string,
  body: { name: string; description?: string; include_participants?: boolean },
) {
  return unwrap(
    await api.POST('/api/v1/projects/{key}/security-levels', { params: { path: { key } }, body }),
  );
}

export async function patchLevel(
  id: string,
  body: { name?: string; description?: string; include_participants?: boolean },
) {
  return unwrap(
    await api.PATCH('/api/v1/security-levels/{level_id}', {
      params: { path: { level_id: id } },
      body,
    }),
  );
}

export async function deleteLevel(id: string) {
  unwrap(
    await api.DELETE('/api/v1/security-levels/{level_id}', { params: { path: { level_id: id } } }),
  );
}

export async function putGrants(id: string, body: { groups: string[]; users: string[] }) {
  return unwrap(
    await api.PUT('/api/v1/security-levels/{level_id}/grants', {
      params: { path: { level_id: id } },
      body,
    }),
  );
}
