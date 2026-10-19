import { api, unwrap } from './client';
import type { ProjectRole } from './types';

export const accessKeys = {
  groups: ['groups'] as const,
  group: (name: string) => ['groups', name] as const,
  groupRoles: (key: string) => ['group-roles', key.toUpperCase()] as const,
  permissions: (key: string) => ['permissions', key.toUpperCase()] as const,
};

export async function fetchGroups() {
  return unwrap(await api.GET('/api/v1/groups')).items;
}

export async function fetchGroup(name: string) {
  return unwrap(await api.GET('/api/v1/groups/{name}', { params: { path: { name } } }));
}

export async function createGroup(body: { name: string; description?: string }) {
  return unwrap(await api.POST('/api/v1/groups', { body }));
}

export async function deleteGroup(name: string) {
  unwrap(await api.DELETE('/api/v1/groups/{name}', { params: { path: { name } } }));
}

export async function addGroupMember(name: string, handle: string) {
  return unwrap(
    await api.PUT('/api/v1/groups/{name}/members/{handle}', {
      params: { path: { name, handle } },
    }),
  );
}

export async function removeGroupMember(name: string, handle: string) {
  return unwrap(
    await api.DELETE('/api/v1/groups/{name}/members/{handle}', {
      params: { path: { name, handle } },
    }),
  );
}

export async function fetchGroupRoles(key: string) {
  return unwrap(await api.GET('/api/v1/projects/{key}/group-roles', { params: { path: { key } } }))
    .items;
}

export async function putGroupRole(key: string, group: string, role: ProjectRole) {
  return unwrap(
    await api.PUT('/api/v1/projects/{key}/group-roles/{group}', {
      params: { path: { key, group } },
      body: { role },
    }),
  );
}

export async function removeGroupRole(key: string, group: string) {
  unwrap(
    await api.DELETE('/api/v1/projects/{key}/group-roles/{group}', {
      params: { path: { key, group } },
    }),
  );
}

export async function fetchPermissions(key: string) {
  return unwrap(await api.GET('/api/v1/projects/{key}/permissions', { params: { path: { key } } }));
}

export async function putPermissions(
  key: string,
  body: { member?: Record<string, boolean>; viewer?: Record<string, boolean> },
) {
  return unwrap(
    await api.PUT('/api/v1/projects/{key}/permissions', { params: { path: { key } }, body }),
  );
}

export async function resetPermissions(key: string) {
  return unwrap(
    await api.DELETE('/api/v1/projects/{key}/permissions', { params: { path: { key } } }),
  );
}
