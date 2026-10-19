import { api, unwrap } from './client';

export type BulkOperation = Record<string, unknown> & { op: string };

export const jobKeys = { detail: (id: string) => ['jobs', id] as const };

export async function cloneTicket(
  key: string,
  body: {
    target_project?: string | null;
    include?: string[];
    area_mapping?: Record<string, string>;
  },
) {
  return unwrap(await api.POST('/api/v1/tickets/{key}/clone', { params: { path: { key } }, body }));
}

export async function moveTicket(
  key: string,
  body: {
    target_project: string;
    area_mapping?: Record<string, string>;
    status_mapping?: Record<string, string>;
    milestone?: string | null;
    include_children?: boolean;
  },
) {
  return unwrap(await api.POST('/api/v1/tickets/{key}/move', { params: { path: { key } }, body }));
}

export async function bulkUpdate(body: {
  keys?: string[] | null;
  query?: string | null;
  operations: BulkOperation[];
  dry_run: boolean;
}) {
  return unwrap(await api.POST('/api/v1/tickets/bulk', { body }));
}

export async function fetchJob(id: string) {
  return unwrap(await api.GET('/api/v1/jobs/{job_id}', { params: { path: { job_id: id } } }));
}
