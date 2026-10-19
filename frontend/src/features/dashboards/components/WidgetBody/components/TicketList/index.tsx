import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../../../components/icons/CategoryIcon';
import { TypeIcon } from '../../../../../../components/icons/TypeIcon';
import { TicketKey } from '../../../../../../components/ui/Badge';
import type { WidgetData } from '../../../../../../services/api/types';
import * as S from './style';

type Props = { tickets: NonNullable<WidgetData['tickets']>; total: number; showBlockers?: boolean };

/** Compact ticket rows; blocked tickets show who blocks them. */
export function TicketList({ tickets, total, showBlockers = false }: Props) {
  const { t } = useTranslation();
  if (tickets.length === 0) return <S.Empty>{t('dashboards.noTickets')}</S.Empty>;
  return (
    <S.List>
      {tickets.map((ticket) => (
        <li key={ticket.key}>
          <TypeIcon type={ticket.type} size={13} />
          <Link to="/t/$key" params={{ key: ticket.key }}>
            <TicketKey>{ticket.key}</TicketKey>
            <span>{ticket.title}</span>
          </Link>
          {showBlockers && ticket.blocked_by.length > 0 ? (
            <S.Blockers>
              {t('dashboards.blockedBy', { keys: ticket.blocked_by.join(', ') })}
            </S.Blockers>
          ) : (
            <S.Status>
              <CategoryIcon category={ticket.status.category} size={12} />
              {ticket.status.name}
            </S.Status>
          )}
        </li>
      ))}
      {total > tickets.length && (
        <S.More>{t('dashboards.more', { count: total - tickets.length })}</S.More>
      )}
    </S.List>
  );
}
