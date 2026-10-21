import type {
  DbColumn,
  DbRow,
  DbView,
  FolioDatabase,
} from '../../../../services/api/folioDatabases';
import { mockFetch } from '../../../../test/renderWithProviders';

export const DB_ID = 'd1000000-0000-4000-8000-000000000001';

export const COLUMNS: DbColumn[] = [
  { key: 'name', name: 'Name', type: 'text', options: {} },
  {
    key: 'status',
    name: 'Status',
    type: 'select',
    options: {
      choices: [
        { value: 'Idea', color: 'grey' },
        { value: 'Trial', color: 'yellow' },
        { value: 'Adopted', color: 'green' },
      ],
    },
  },
  { key: 'owner', name: 'Owner', type: 'person', options: {} },
  { key: 'seats', name: 'Seats', type: 'number', options: {} },
  { key: 'paid', name: 'Paid', type: 'checkbox', options: {} },
];

const keys = COLUMNS.map((c) => c.key);
export const VIEWS: DbView[] = [
  {
    id: 'table',
    name: 'Table',
    kind: 'table',
    group_by: null,
    filters: [],
    sort: [],
    visible_columns: keys,
  },
  {
    id: 'board',
    name: 'Board',
    kind: 'board',
    group_by: 'status',
    filters: [],
    sort: [],
    visible_columns: keys,
  },
  {
    id: 'cards',
    name: 'Cards',
    kind: 'cards',
    group_by: null,
    filters: [],
    sort: [],
    visible_columns: keys,
  },
];

export const ROWS: DbRow[] = [
  {
    id: 'r1',
    values: { name: 'Claude', status: 'Adopted', owner: 'vera', seats: 12, paid: true },
    updated_at: '2026-10-21T10:00:00Z',
  },
  { id: 'r2', values: { name: 'Devin', status: 'Idea' }, updated_at: '2026-10-21T10:00:00Z' },
  { id: 'r3', values: { name: 'Sin estado' }, updated_at: '2026-10-21T10:00:00Z' },
];

export const DATABASE: FolioDatabase = {
  node_id: DB_ID,
  title: 'Inventario',
  space: 'ai-tools',
  can_edit: true,
  columns: COLUMNS,
  views: VIEWS,
  cleared: 0,
};

/** The database API, with `extra` handlers on top. */
export function dbApi(
  database: FolioDatabase = DATABASE,
  extra: Parameters<typeof mockFetch>[0] = {},
) {
  return mockFetch({
    [`GET /api/v1/folio/databases/${DB_ID}`]: { status: 200, body: database },
    [`GET /api/v1/folio/databases/${DB_ID}/rows`]: (request) => {
      const id = new URL(request.url).searchParams.get('view') ?? 'table';
      const view = database.views.find((v) => v.id === id) ?? database.views[0];
      return { status: 200, body: { view, columns: database.columns, items: ROWS } };
    },
    ...extra,
  });
}
