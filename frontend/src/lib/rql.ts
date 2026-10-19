/** Quote a value for RQL when it is not a bare word. */
export function rqlValue(value: string): string {
  return /^[A-Za-z0-9_@][A-Za-z0-9_.:@-]*$/.test(value)
    ? value
    : `"${value.replace(/["\\]/g, '\\$&')}"`;
}

export type BoardFilters = {
  type?: string;
  area?: string;
  milestone?: string;
  assignee?: string;
  tag?: string;
};

/** RQL clauses for the board filters, joined with AND. */
export function filterClauses(filters: BoardFilters): string[] {
  const clauses: string[] = [];
  if (filters.type) clauses.push(`type = ${rqlValue(filters.type)}`);
  if (filters.area) {
    clauses.push(filters.area === '-' ? 'area IS EMPTY' : `area = ${rqlValue(filters.area)}`);
  }
  if (filters.milestone) {
    clauses.push(
      filters.milestone === '-'
        ? 'milestone IS EMPTY'
        : `milestone = ${rqlValue(filters.milestone)}`,
    );
  }
  if (filters.assignee) {
    clauses.push(
      filters.assignee === '-'
        ? 'assignee IS EMPTY'
        : filters.assignee === 'me'
          ? 'assignee = currentUser()'
          : `assignee = ${rqlValue(filters.assignee)}`,
    );
  }
  if (filters.tag) clauses.push(`tag = ${rqlValue(filters.tag)}`);
  return clauses;
}
