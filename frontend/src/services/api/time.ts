import { api, unwrap } from './client';

export const timeKeys = {
  voters: (key: string) => ['voters', key.toUpperCase()] as const,
  worklogs: (key: string) => ['worklogs', key.toUpperCase()] as const,
};

const path = (key: string) => ({ params: { path: { key } } });

export async function setVote(key: string, voted: boolean) {
  return voted
    ? unwrap(await api.PUT('/api/v1/tickets/{key}/vote', path(key)))
    : unwrap(await api.DELETE('/api/v1/tickets/{key}/vote', path(key)));
}

export async function fetchVoters(key: string) {
  return unwrap(await api.GET('/api/v1/tickets/{key}/voters', path(key))).items;
}

export async function fetchWorklogs(key: string) {
  return unwrap(await api.GET('/api/v1/tickets/{key}/worklogs', path(key))).items;
}

export async function addWorklog(
  key: string,
  body: { minutes: number; started_at?: string | null; description?: string | null },
) {
  return unwrap(await api.POST('/api/v1/tickets/{key}/worklogs', { ...path(key), body }));
}

export async function patchWorklog(
  id: string,
  body: { minutes?: number; started_at?: string; description?: string | null },
) {
  return unwrap(
    await api.PATCH('/api/v1/worklogs/{worklog_id}', {
      params: { path: { worklog_id: id } },
      body,
    }),
  );
}

export async function deleteWorklog(id: string) {
  unwrap(
    await api.DELETE('/api/v1/worklogs/{worklog_id}', { params: { path: { worklog_id: id } } }),
  );
}
