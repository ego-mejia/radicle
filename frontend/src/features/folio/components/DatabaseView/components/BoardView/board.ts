import type { DbColumn, DbRow } from '../../../../../../services/api/folioDatabases';

export const NONE = '__none__';

/** The groups of a board: one per choice, in order, and "No value" when a row has none. */
export function groupsOf(group: DbColumn, rows: DbRow[]) {
  const choices = (group.options.choices ?? []).map((c) => c.value);
  const of = (r: DbRow) => {
    const v = r.values[group.key];
    return typeof v === 'string' && choices.includes(v) ? v : NONE;
  };
  const out = choices.map((value) => ({ value, rows: rows.filter((r) => of(r) === value) }));
  const none = rows.filter((r) => of(r) === NONE);
  return none.length ? [{ value: NONE, rows: none }, ...out] : out;
}

/** The move a drop makes: the row and its new value, or null when it stays where it is. */
export function dropFor(
  group: DbColumn,
  rows: DbRow[],
  rowId: string,
  over: string,
): { row: DbRow; value: string | null } | null {
  const row = rows.find((r) => r.id === rowId);
  const value = over === NONE ? null : over;
  if (!row || (row.values[group.key] ?? null) === value) return null;
  return { row, value };
}
