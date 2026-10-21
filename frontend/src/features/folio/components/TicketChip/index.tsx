import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { fetchTicketPreview, ticketKeys } from '../../../../services/api/folioTickets';
import * as S from './style';

/** A Docket ticket's smart link (Folio 4.1): key, title, status and assignee, refreshed
 * while the page is open. A ticket the reader can't see in Docket shows as restricted. */
export function TicketChip({ ticketKey }: { ticketKey: string }) {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: ticketKeys.preview(ticketKey),
    queryFn: () => fetchTicketPreview(ticketKey),
    staleTime: 15 * 1000,
    refetchInterval: 30 * 1000,
  });
  const ticket = data?.ticket;
  if (data && !ticket) {
    return (
      <S.Chip data-ticket={ticketKey}>
        <S.Muted>{t('folio.tickets.restricted')}</S.Muted>
      </S.Chip>
    );
  }
  return (
    <S.Chip data-ticket={ticketKey} aria-busy={!data}>
      <Link to="/t/$key" params={{ key: ticketKey }}>
        <S.Key>{ticketKey}</S.Key>
      </Link>
      {ticket ? (
        <>
          <S.Title title={ticket.title}>{ticket.title}</S.Title>
          <S.State $category={ticket.status_category}>{ticket.status}</S.State>
          <S.Muted>
            {ticket.assignee ? `@${ticket.assignee.handle}` : t('folio.tickets.unassigned')}
          </S.Muted>
        </>
      ) : null}
    </S.Chip>
  );
}
