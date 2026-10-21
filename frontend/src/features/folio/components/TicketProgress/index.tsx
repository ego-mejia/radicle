import { useQuery } from '@tanstack/react-query';
import { Link, useRouterState } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { isApiError } from '../../../../services/api/client';
import { fetchBuildSpecItems, ticketKeys } from '../../../../services/api/folioTickets';
import { State } from '../TicketChip/style';
import * as S from './style';

const PAGE = /^\/folio\/p\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/;

/** The Ticket progress block (Folio 4.3): on a build spec, each deliverable with its
 * Docket ticket's status, assignee and checklist, refreshed while the page is open. It
 * reads the page it sits on from the URL (`/folio/p/<id>-<slug>`). */
export function TicketProgress({ title }: { title?: string | null }) {
  const { t } = useTranslation();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const nodeId = PAGE.exec(path)?.[1] ?? null;
  const { data, error } = useQuery({
    queryKey: ticketKeys.buildSpec(nodeId ?? ''),
    queryFn: () => fetchBuildSpecItems(nodeId ?? ''),
    enabled: !!nodeId,
    staleTime: 15 * 1000,
    refetchInterval: 60 * 1000,
    retry: false,
  });
  const items = data ?? [];
  const heading = title || t('folio.buildSpec.progress');
  return (
    <S.Box aria-label={heading}>
      <S.Head>
        <strong>{heading}</strong>
        {data ? (
          <S.Muted>
            {t('folio.buildSpec.done', {
              done: items.filter((i) => i.ticket?.status_category === 'done').length,
              total: items.length,
            })}
          </S.Muted>
        ) : null}
      </S.Head>
      {!nodeId ? (
        <S.Muted>{t('folio.buildSpec.onlyHere')}</S.Muted>
      ) : error ? (
        <S.Error role="alert">
          {isApiError(error) ? error.message : t('folio.buildSpec.failed')}
        </S.Error>
      ) : data && !items.length ? (
        <S.Muted>{t('folio.buildSpec.empty')}</S.Muted>
      ) : (
        <S.List aria-busy={!data}>
          {items.map((item) => {
            const ticket = item.ticket;
            const total = ticket?.checklist_total ?? 0;
            return (
              <S.Item key={item.key}>
                <S.Key>{item.key}</S.Key>
                <S.Title>{item.title}</S.Title>
                {ticket ? (
                  <>
                    <Link to="/t/$key" params={{ key: ticket.key }}>
                      {ticket.key}
                    </Link>
                    <State $category={ticket.status_category}>{ticket.status}</State>
                    <S.Muted>
                      {ticket.assignee
                        ? `@${ticket.assignee.handle}`
                        : t('folio.tickets.unassigned')}
                    </S.Muted>
                    <S.Bar
                      role="progressbar"
                      aria-label={t('folio.buildSpec.checklist', { key: ticket.key })}
                      aria-valuemin={0}
                      aria-valuemax={total}
                      aria-valuenow={ticket.checklist_done}
                      $done={total ? ticket.checklist_done / total : 0}
                    >
                      {total ? `${ticket.checklist_done}/${total}` : '—'}
                    </S.Bar>
                  </>
                ) : (
                  <S.Pending>
                    {item.linked ? t('folio.tickets.restricted') : t('folio.buildSpec.noTicket')}
                  </S.Pending>
                )}
              </S.Item>
            );
          })}
        </S.List>
      )}
    </S.Box>
  );
}
