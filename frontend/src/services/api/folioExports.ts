import { api, unwrap } from './client';
import type { components } from './schema';

export type FolioExport = components['schemas']['ExportOut'];
export type ExportFormat = FolioExport['format'];
export type ExportTarget = { node: string } | { space: string };

export const exportKeys = {
  one: (id: string) => ['folio', 'exports', id] as const,
};

export async function createExport(target: ExportTarget, format: ExportFormat) {
  return unwrap(await api.POST('/api/v1/folio/exports', { body: { ...target, format } }));
}

export async function fetchExport(id: string): Promise<FolioExport> {
  return unwrap(
    await api.GET('/api/v1/folio/exports/{export_id}', { params: { path: { export_id: id } } }),
  );
}
