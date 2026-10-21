import type { DbColumn, DbRows } from '../../../../services/api/folioDatabases';

/** The columns a view shows, in its order. */
export function shown(rows: DbRows): DbColumn[] {
  const byKey = new Map(rows.columns.map((c) => [c.key, c]));
  return rows.view.visible_columns.flatMap((k) => byKey.get(k) ?? []);
}
