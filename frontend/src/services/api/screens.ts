import { api, unwrap } from './client';
import type { ScreenIn, ScreenOperation, TicketType } from './types';

export const screenKeys = {
  schema: (project: string, type: string, operation: string, transition?: string) =>
    ['schema', project.toUpperCase(), type, operation, transition ?? ''] as const,
  list: (project: string) => ['screens', project.toUpperCase()] as const,
};

export async function fetchSchema(
  project: string,
  type: TicketType,
  operation: ScreenOperation = 'create',
  transition?: string,
) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/schema', {
      params: { path: { key: project }, query: { type, operation, transition } },
    }),
  );
}

export async function fetchScreens(project: string) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/screens', { params: { path: { key: project } } }),
  ).items;
}

export async function putScreens(project: string, screens: ScreenIn[]) {
  return unwrap(
    await api.PUT('/api/v1/projects/{key}/screens', {
      params: { path: { key: project } },
      body: { screens },
    }),
  ).items;
}
