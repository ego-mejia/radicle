/** The Filter button of List: chosen values per field, turned into RQL. */
export type ListFilters = {
  type: string[];
  category: string[];
  priority: string[];
  /** Handles, plus `@me` (currentUser()) and `@none` (unassigned). */
  assignee: string[];
  area: string[];
  milestone: string[];
};

export const FILTER_FIELDS = [
  'type',
  'category',
  'priority',
  'assignee',
  'area',
  'milestone',
] as const;

export const NO_FILTERS: ListFilters = {
  type: [],
  category: [],
  priority: [],
  assignee: [],
  area: [],
  milestone: [],
};

const quote = (v: string) => (/^[\w.-]+$/.test(v) ? v : `"${v.replace(/"/g, '\\"')}"`);

function clause(field: string, values: string[]): string | null {
  if (values.length === 0) return null;
  const none = values.includes('@none');
  const listed = values
    .filter((v) => v !== '@none')
    .map((v) => (v === '@me' ? 'currentUser()' : quote(v)));
  const parts = [
    ...(listed.length === 1 ? [`${field} = ${listed[0]}`] : []),
    ...(listed.length > 1 ? [`${field} IN (${listed.join(', ')})`] : []),
    ...(none ? [`${field} IS EMPTY`] : []),
  ];
  return parts.length > 1 ? `(${parts.join(' OR ')})` : (parts[0] ?? null);
}

/** RQL for the chosen filters, or '' when none. */
export function filtersToRql(filters: ListFilters): string {
  return FILTER_FIELDS.map((f) => clause(f, filters[f]))
    .filter((c): c is string => c !== null)
    .join(' AND ');
}

export function filterCount(filters: ListFilters): number {
  return FILTER_FIELDS.reduce((n, f) => n + filters[f].length, 0);
}

/** `query` narrowed by the filters, keeping its ORDER BY at the end. */
export function applyFilters(query: string, filters: ListFilters): string {
  const extra = filtersToRql(filters);
  if (!extra) return query;
  const match = /\s*\bORDER\s+BY\b/i.exec(query);
  const where = (match ? query.slice(0, match.index) : query).trim();
  const order = match ? query.slice(match.index).trim() : '';
  const combined = where ? `(${where}) AND ${extra}` : extra;
  return order ? `${combined} ${order}` : combined;
}

/** Filters in the URL as compact JSON; anything unreadable means no filters. */
export function decodeFilters(raw: string | undefined): ListFilters {
  if (!raw) return NO_FILTERS;
  try {
    const parsed = JSON.parse(raw) as Partial<Record<string, unknown>>;
    const out = { ...NO_FILTERS };
    for (const f of FILTER_FIELDS) {
      const v = parsed[f];
      if (Array.isArray(v)) out[f] = v.filter((x): x is string => typeof x === 'string');
    }
    return out;
  } catch {
    return NO_FILTERS;
  }
}

export function encodeFilters(filters: ListFilters): string | undefined {
  if (filterCount(filters) === 0) return undefined;
  const compact = Object.fromEntries(
    FILTER_FIELDS.filter((f) => filters[f].length).map((f) => [f, filters[f]]),
  );
  return JSON.stringify(compact);
}
