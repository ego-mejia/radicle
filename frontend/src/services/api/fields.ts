import { api, unwrap } from './client';
import type { CustomFieldCreate, CustomFieldPatch } from './types';

export const fieldKeys = {
  list: (key: string, archived: boolean) => ['fields', key.toUpperCase(), archived] as const,
};

export async function fetchFields(key: string, includeArchived = false) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/fields', {
      params: { path: { key }, query: { include_archived: includeArchived } },
    }),
  ).items;
}

export async function createField(key: string, body: CustomFieldCreate) {
  return unwrap(
    await api.POST('/api/v1/projects/{key}/fields', { params: { path: { key } }, body }),
  );
}

export async function patchField(key: string, fieldKey: string, body: CustomFieldPatch) {
  return unwrap(
    await api.PATCH('/api/v1/projects/{key}/fields/{field_key}', {
      params: { path: { key, field_key: fieldKey } },
      body,
    }),
  );
}
