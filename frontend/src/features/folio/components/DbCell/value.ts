import type { DbColumn } from '../../../../services/api/folioDatabases';

/** What an input's text means for a column: a number, a handle without @, or null when
 * empty. The server checks the rest and says what's wrong. */
export function fromInput(column: DbColumn, text: string): unknown {
  const v = text.trim();
  if (!v) return null;
  if (column.type === 'number') return Number.isNaN(Number(v)) ? v : Number(v);
  if (column.type === 'person') return v.replace(/^@/, '').toLowerCase();
  return v;
}
