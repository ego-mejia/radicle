import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { isApiError } from '../../../../services/api/client';
import { queryTickets, ticketKeys } from '../../../../services/api/folioTickets';
import { State } from '../TicketChip/style';
import * as S from './style';

type Props = { rql: string; title?: string | null; limit?: number | null };

/** The ticket table block (Folio 4.1): Docket tickets by RQL, as Docket shows them to this
 * reader, refreshed while the page is open. A query Docket can't run says why. */
export function TicketTable({ rql, title, limit }: Props) {
  const { t } = useTranslation();
  const size = limit ?? 25;
  const { data, error } = useQuery({
    queryKey: ticketKeys.query(rql, size),
    queryFn: () => queryTickets(rql, size),
    staleTime: 15 * 1000,
    refetchInterval: 60 * 1000,
    retry: false,
  });
  const items = data?.items ?? [];
  return (
    <S.Box aria-label={title || t('folio.tickets.table')}>
      <S.Head>
        <strong>{title || t('folio.tickets.table')}</strong>
        <S.Rql>{rql}</S.Rql>
      </S.Head>
      {error ? (
        <S.Error role="alert">
          {isApiError(error) ? error.message : t('folio.tickets.tableFailed')}
        </S.Error>
      ) : data && !items.length ? (
        <S.Muted>{t('folio.tickets.tableEmpty')}</S.Muted>
      ) : (
        <S.Table aria-busy={!data}>
          <thead>
            <tr>
              <th>{t('folio.tickets.key')}</th>
              <th>{t('folio.tickets.title')}</th>
              <th>{t('folio.tickets.status')}</th>
              <th>{t('folio.tickets.assignee')}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((ticket) => (
              <tr key={ticket.key}>
                <td>
                  <Link to="/t/$key" params={{ key: ticket.key }}>
                    {ticket.key}
                  </Link>
                </td>
                <td>{ticket.title}</td>
                <td>
                  <State $category={ticket.status_category}>{ticket.status}</State>
                </td>
                <td>
                  {ticket.assignee ? `@${ticket.assignee.handle}` : t('folio.tickets.unassigned')}
                </td>
              </tr>
            ))}
          </tbody>
        </S.Table>
      )}
      {data && data.total > items.length ? (
        <S.Muted>{t('folio.tickets.showing', { shown: items.length, total: data.total })}</S.Muted>
      ) : null}
    </S.Box>
  );
}
