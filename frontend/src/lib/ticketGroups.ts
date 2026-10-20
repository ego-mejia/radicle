import type { TicketSummary } from '../services/api/types';

export type GroupBy = 'none' | 'type' | 'status' | 'priority' | 'assignee' | 'area' | 'milestone';
export const GROUP_BYS: GroupBy[] = [
  'none',
  'type',
  'status',
  'priority',
  'assignee',
  'area',
  'milestone',
];

export type TicketGroup = { id: string; label: string | null; tickets: TicketSummary[] };

function valueOf(t: TicketSummary, by: GroupBy): string | null {
  switch (by) {
    case 'type':
      return t.type;
    case 'status':
      return t.status.name;
    case 'priority':
      return t.priority;
    case 'assignee':
      return t.assignee?.handle ?? null;
    case 'area':
      return t.area;
    case 'milestone':
      return t.milestone;
    default:
      return null;
  }
}

/** Tickets split by a field, in the order each value first appears; empty values last. */
export function groupTickets(tickets: TicketSummary[], by: GroupBy): TicketGroup[] {
  if (by === 'none') return [{ id: 'all', label: null, tickets }];
  const groups = new Map<string, TicketGroup>();
  for (const t of tickets) {
    const value = valueOf(t, by);
    const id = value ?? '\u0000none';
    if (!groups.has(id)) groups.set(id, { id, label: value, tickets: [] });
    groups.get(id)!.tickets.push(t);
  }
  return [...groups.values()].sort((a, b) => Number(a.label === null) - Number(b.label === null));
}

/** Top-level rows: tickets whose parent is not among them. Their subtickets nest. */
export function topLevel(tickets: TicketSummary[]): TicketSummary[] {
  const keys = new Set(tickets.map((t) => t.key));
  return tickets.filter((t) => !t.parent || !keys.has(t.parent));
}
