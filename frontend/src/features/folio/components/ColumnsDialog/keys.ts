import { type DbColumn, columnKey } from '../../../../services/api/folioDatabases';

/** New columns (key '') get a key from their name; existing keys never change. */
export function withKeys(columns: DbColumn[]): DbColumn[] {
  const taken = columns.map((c) => c.key).filter(Boolean);
  return columns.map((c) => {
    if (c.key) return c;
    const key = columnKey(c.name, taken);
    taken.push(key);
    return { ...c, key };
  });
}
