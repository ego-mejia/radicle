import { useQuery } from '@tanstack/react-query';
import { filterClauses, type BoardFilters } from '../../../lib/rql';
import { searchAll, ticketKeys } from '../../../services/api/tickets';
import type { Category, TicketSummary } from '../../../services/api/types';

export const DONE_WINDOW_DAYS = 14;

/** Open tickets plus those done in the last 14 days, grouped by status category. */
export function useBoard(project: string, filters: BoardFilters) {
  const base = [`project = ${project}`, ...filterClauses(filters)].join(' AND ');
  const openQ = `${base} AND category != done ORDER BY rank`;
  const doneQ = `${base} AND category = done AND resolved >= -${DONE_WINDOW_DAYS}d ORDER BY rank`;
  const open = useQuery({ queryKey: ticketKeys.search(openQ), queryFn: () => searchAll(openQ) });
  const done = useQuery({ queryKey: ticketKeys.search(doneQ), queryFn: () => searchAll(doneQ) });
  const columns: Record<Category, TicketSummary[]> = { todo: [], in_progress: [], done: [] };
  for (const ticket of open.data?.items ?? []) columns[ticket.status.category].push(ticket);
  columns.done = done.data?.items ?? [];
  return {
    columns,
    isPending: open.isPending || done.isPending,
    error: open.error ?? done.error,
    allDoneQuery: `${base} AND category = done ORDER BY resolved DESC`,
  };
}
