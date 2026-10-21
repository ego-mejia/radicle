// Folio databases (3.6): columns and views, and the rows each view shows.

import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type DbRow = S['DbRowOut'];

export type ColumnType =
  'text' | 'number' | 'date' | 'select' | 'multi_select' | 'person' | 'checkbox' | 'url' | 'page';
export const COLUMN_TYPES: ColumnType[] = [
  'text',
  'number',
  'date',
  'select',
  'multi_select',
  'person',
  'checkbox',
  'url',
  'page',
];
export type ChoiceColor = 'grey' | 'blue' | 'green' | 'yellow' | 'red' | 'purple';
export const CHOICE_COLORS: ChoiceColor[] = ['grey', 'blue', 'green', 'yellow', 'red', 'purple'];
export type DbChoice = { value: string; color: ChoiceColor };
export type DbColumn = {
  key: string;
  name: string;
  type: ColumnType;
  options: { choices?: DbChoice[] };
};

export type ViewKind = 'table' | 'cards' | 'board';
export type FilterOp =
  'eq' | 'neq' | 'contains' | 'gt' | 'gte' | 'lt' | 'lte' | 'empty' | 'not_empty';
export const FILTER_OPS: FilterOp[] = [
  'eq',
  'neq',
  'contains',
  'gt',
  'gte',
  'lt',
  'lte',
  'empty',
  'not_empty',
];
export type DbFilter = { column: string; op: FilterOp; value?: unknown };
export type DbSort = { column: string; direction: 'asc' | 'desc' };
export type DbView = {
  id: string;
  name: string;
  kind: ViewKind;
  group_by: string | null;
  filters: DbFilter[];
  sort: DbSort[];
  visible_columns: string[];
};

export type FolioDatabase = Omit<S['DatabaseOut'], 'columns' | 'views'> & {
  columns: DbColumn[];
  views: DbView[];
};
export type DbRows = { view: DbView; columns: DbColumn[]; items: DbRow[] };
export type DbValues = Record<string, unknown>;

export const dbKeys = {
  database: (id: string) => ['folio', 'databases', id] as const,
  rows: (id: string, view?: string) => ['folio', 'databases', id, 'rows', view ?? ''] as const,
};

export async function fetchDatabase(id: string): Promise<FolioDatabase> {
  return unwrap(
    await api.GET('/api/v1/folio/databases/{node_id}', { params: { path: { node_id: id } } }),
  ) as FolioDatabase;
}

export async function patchDatabase(
  id: string,
  body: { columns?: DbColumn[]; views?: DbView[] },
): Promise<FolioDatabase> {
  return unwrap(
    await api.PATCH('/api/v1/folio/databases/{node_id}', {
      params: { path: { node_id: id } },
      body: body as S['DatabasePatch'],
    }),
  ) as FolioDatabase;
}

export async function fetchRows(id: string, view?: string): Promise<DbRows> {
  return unwrap(
    await api.GET('/api/v1/folio/databases/{node_id}/rows', {
      params: { path: { node_id: id }, query: { view } },
    }),
  ) as DbRows;
}

export async function addRow(id: string, values: DbValues): Promise<DbRow> {
  return unwrap(
    await api.POST('/api/v1/folio/databases/{node_id}/rows', {
      params: { path: { node_id: id } },
      body: { values },
    }),
  );
}

export async function patchRow(
  id: string,
  body: { values?: DbValues; after?: string; to_top?: boolean },
): Promise<DbRow> {
  return unwrap(
    await api.PATCH('/api/v1/folio/rows/{row_id}', { params: { path: { row_id: id } }, body }),
  );
}

export async function deleteRow(id: string): Promise<void> {
  unwrap(await api.DELETE('/api/v1/folio/rows/{row_id}', { params: { path: { row_id: id } } }));
}

/** A column key from its name, not taken by `taken`: `Fecha de alta` → `fecha_de_alta`. */
export function columnKey(name: string, taken: string[]): string {
  const base =
    name
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 32) || 'column';
  let key = base;
  for (let n = 2; taken.includes(key); n++) key = `${base}_${n}`;
  return key;
}
