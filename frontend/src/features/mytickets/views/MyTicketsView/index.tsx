import { useNavigate, useSearch } from '@tanstack/react-router';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { TicketTable } from '../../../../components/TicketTable';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useTicketSearch } from '../../../list/hooks/useTicketSearch';
import { TicketPanel } from '../../../tickets/components/TicketPanel';

export const MY_TICKETS_QUERY =
  'assignee = currentUser() AND category != done ORDER BY priority DESC, due ASC';

/** Open tickets assigned to me in every project. */
export function MyTicketsView() {
  const { t } = useTranslation();
  const { t: openKey } = useSearch({ from: '/app/me/tickets' });
  const navigate = useNavigate({ from: '/me/tickets' });
  const search = useTicketSearch(MY_TICKETS_QUERY);
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = search;
  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  return (
    <>
      <PageTitle title={t('nav.myTickets')} subtitle={t('myTickets.subtitle')} />
      {search.isPending ? (
        <PageSpinner />
      ) : search.items.length === 0 ? (
        <EmptyState plant="pot" title={t('myTickets.emptyTitle')} text={t('myTickets.emptyText')} />
      ) : (
        <TicketTable
          tickets={search.items}
          total={search.total}
          onOpen={(key) => void navigate({ search: { t: key } })}
          hasMore={!!hasNextPage}
          loadingMore={isFetchingNextPage}
          onLoadMore={loadMore}
        />
      )}
      <TicketPanel
        ticketKey={openKey}
        onClose={() => void navigate({ search: { t: undefined } })}
      />
    </>
  );
}
