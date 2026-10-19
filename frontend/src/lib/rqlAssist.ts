import type { SearchFields } from '../services/api/types';

export type Suggestion = { label: string; insert: string; detail?: string };

const KEYWORDS_AFTER_CLAUSE = ['AND', 'OR', 'ORDER BY'];

function quote(value: string): string {
  return /^[A-Za-z0-9_@][A-Za-z0-9_.:@-]*$/.test(value) ? value : `"${value}"`;
}

/** Split off the word being typed at the end of `text`. */
function lastWord(text: string): { before: string; word: string } {
  const match = /("[^"]*|[^\s(),"]*)$/.exec(text);
  const word = match ? match[1]! : '';
  return { before: text.slice(0, text.length - word.length), word };
}

/**
 * Suggestions for the cursor position: fields at the start of a term, operators after
 * a field, values after an operator, keywords after a complete clause.
 */
export function suggest(
  text: string,
  meta: SearchFields | undefined,
): { from: number; items: Suggestion[] } {
  const { before, word } = lastWord(text);
  const from = before.length;
  if (!meta) return { from, items: [] };
  const tokens = before.trim().split(/\s+/).filter(Boolean);
  const prev = tokens[tokens.length - 1] ?? '';
  const prev2 = tokens[tokens.length - 2] ?? '';
  const custom = meta.values?.custom_fields ?? [];
  const fields = [...meta.fields, ...custom];
  const fieldNames = fields.map((f) => f.name);
  const lower = word.toLowerCase().replace(/^"/, '');
  const match = (items: Suggestion[]) =>
    items
      .filter((s) => s.label.toLowerCase().startsWith(lower) && s.label.toLowerCase() !== lower)
      .slice(0, 12);

  if (/^order$/i.test(prev2) && /^by$/i.test(prev)) {
    return { from, items: match(meta.sort_fields.map((f) => ({ label: f, insert: `${f} ` }))) };
  }
  const field = fields.find((f) => f.name === prev.toLowerCase());
  if (field) {
    const ops = [
      ...field.operators,
      ...(field.supports_in ? ['IN'] : []),
      ...(field.supports_empty ? ['IS EMPTY'] : []),
    ];
    return { from, items: match(ops.map((op) => ({ label: op, insert: `${op} ` }))) };
  }
  const opField = fields.find((f) => f.name === prev2.toLowerCase());
  if (opField && opField.operators.includes(prev)) {
    const kind =
      opField.name.startsWith('cf.') && opField.type === 'user' ? 'assignee' : opField.name;
    return { from, items: match(valuesFor(kind, opField.values ?? [], meta)) };
  }
  if (!tokens.length || /^(and|or|not|\()$/i.test(prev) || prev.endsWith('(')) {
    return {
      from,
      items: match(fields.map((f) => ({ label: f.name, insert: `${f.name} `, detail: f.type }))),
    };
  }
  if (fieldNames.includes(prev2.toLowerCase()) || prev.endsWith(')') || prev.startsWith('#')) {
    return {
      from,
      items: match(KEYWORDS_AFTER_CLAUSE.map((k) => ({ label: k, insert: `${k} ` }))),
    };
  }
  return { from, items: [] };
}

function valuesFor(field: string, enumValues: string[], meta: SearchFields): Suggestion[] {
  const v = meta.values;
  const list = (items: string[]) => items.map((x) => ({ label: x, insert: `${quote(x)} ` }));
  switch (field) {
    case 'status':
      return list(v?.statuses ?? []);
    case 'area':
      return list(v?.areas ?? []);
    case 'milestone':
      return list(v?.milestones ?? []);
    case 'assignee':
    case 'reporter':
    case 'collaborator':
      return [{ label: 'currentUser()', insert: 'currentUser() ' }, ...list(v?.handles ?? [])];
    case 'tag':
      return list(v?.tags ?? []);
    case 'project':
      return v ? list([v.project]) : [];
    case 'due':
    case 'created':
    case 'updated':
    case 'resolved':
      return list(['-7d', '+3d', 'startOfWeek()', 'startOfMonth()', 'now()']);
    default:
      return list(enumValues);
  }
}

/** Replace or add the ORDER BY clause, toggling direction when the field is the same. */
export function withOrder(query: string, field: string): string {
  const [where, order] = query.split(/\s*\bORDER\s+BY\b\s*/i);
  const current = (order ?? '').trim().split(',')[0]?.trim().split(/\s+/) ?? [];
  const sameField = current[0]?.toLowerCase() === field;
  const direction = sameField && current[1]?.toUpperCase() !== 'DESC' ? 'DESC' : 'ASC';
  const base = (where ?? '').trim();
  return `${base}${base ? ' ' : ''}ORDER BY ${field} ${direction}`;
}

export function currentOrder(query: string): { field: string; desc: boolean } | null {
  const order = query.split(/\bORDER\s+BY\b/i)[1];
  const first = order?.trim().split(',')[0]?.trim().split(/\s+/);
  if (!first?.[0]) return null;
  return { field: first[0].toLowerCase(), desc: first[1]?.toUpperCase() === 'DESC' };
}
