import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type FolioImportSource = S['ImportOut']['source'];
export type FolioImportOptions = S['ImportOptionsIn'];

/** One page of the dry run's plan (Folio 5.3). */
export type ImportPlanPage = {
  external_id: string;
  title: string;
  kind: 'page' | 'folder' | 'database';
  parent_id: string | null;
  action: 'create' | 'update';
  author: string | null;
  labels: string[];
  attachments: number;
  rows: number;
  errors: string[];
};
export type ImportPlanAuthor = {
  source: string;
  user: { id: string; handle: string; name: string } | null;
};
export type ImportPlan = {
  pages: ImportPlanPage[];
  authors: ImportPlanAuthor[];
  errors: string[];
  totals: Record<
    'pages' | 'folders' | 'databases' | 'attachments' | 'updates' | 'with_errors',
    number
  >;
};
/** What the run did with each page. */
export type ImportRunPage = {
  external_id: string;
  title: string;
  action: 'created' | 'updated' | 'failed';
  node_id?: string;
  published?: boolean;
  missing?: string[];
  errors: string[];
};
export type FolioImport = Omit<S['ImportOut'], 'report' | 'stats'> & {
  report: Partial<ImportPlan> & { run?: ImportRunPage[] };
  stats: Partial<Record<'created' | 'updated' | 'failed' | 'published' | 'drafts', number>> & {
    error?: string;
  };
};

export const importKeys = {
  all: ['folio', 'imports'] as const,
  one: (id: string) => ['folio', 'imports', id] as const,
};

export async function fetchImports(): Promise<FolioImport[]> {
  return unwrap(await api.GET('/api/v1/folio/imports')).items as FolioImport[];
}

export async function fetchImport(id: string): Promise<FolioImport> {
  return unwrap(
    await api.GET('/api/v1/folio/imports/{import_id}', { params: { path: { import_id: id } } }),
  ) as FolioImport;
}

export async function createImport(
  space: string,
  source: FolioImportSource,
  file: File,
): Promise<FolioImport> {
  const body = new FormData();
  body.append('file', file);
  body.append('source', source);
  body.append('space', space);
  return unwrap(
    // openapi-fetch sends FormData as is.
    await api.POST('/api/v1/folio/imports', { body: body as never }),
  ) as FolioImport;
}

export async function dryRunImport(id: string, options: FolioImportOptions): Promise<FolioImport> {
  return unwrap(
    await api.POST('/api/v1/folio/imports/{import_id}/dry-run', {
      params: { path: { import_id: id } },
      body: options,
    }),
  ) as FolioImport;
}

export async function runImport(id: string): Promise<FolioImport> {
  return unwrap(
    await api.POST('/api/v1/folio/imports/{import_id}/run', {
      params: { path: { import_id: id } },
    }),
  ) as FolioImport;
}
