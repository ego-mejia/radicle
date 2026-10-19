import { useInfiniteQuery } from '@tanstack/react-query';
import { searchTickets, ticketKeys } from '../../../services/api/tickets';

/** Paged RQL search for tables with infinite scroll. */
export function useTicketSearch(q: string) {
  const query = useInfiniteQuery({
    queryKey: [...ticketKeys.search(q), 'infinite'],
    queryFn: ({ pageParam }) => searchTickets(q, pageParam, 50),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    retry: false,
  });
  const pages = query.data?.pages ?? [];
  return {
    ...query,
    items: pages.flatMap((p) => p.items),
    total: pages[0]?.total ?? 0,
    warnings: pages[0]?.warnings ?? [],
  };
}
