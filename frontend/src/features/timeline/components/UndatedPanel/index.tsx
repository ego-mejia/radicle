import { useTranslation } from 'react-i18next';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { TicketKey } from '../../../../components/ui/Badge';
import type { TimelineTicket } from '../../../../services/api/types';
import { DRAG_TYPE } from '../../../../lib/timeline';
import * as S from './style';

type Props = { tickets: TimelineTicket[]; canEdit: boolean; onOpen: (key: string) => void };

/** Tickets without dates; drag one onto the timeline to give it dates. */
export function UndatedPanel({ tickets, canEdit, onOpen }: Props) {
  const { t } = useTranslation();
  return (
    <S.Panel aria-label={t('timeline.undated')}>
      <h2>
        {t('timeline.undated')} <small>{tickets.length}</small>
      </h2>
      {canEdit && tickets.length > 0 && <S.Help>{t('timeline.undatedHelp')}</S.Help>}
      <S.List>
        {tickets.map((ticket) => (
          <li
            key={ticket.key}
            draggable={canEdit}
            onDragStart={(e) => {
              e.dataTransfer.setData(DRAG_TYPE, ticket.key);
              e.dataTransfer.effectAllowed = 'move';
            }}
            data-testid={`undated-${ticket.key}`}
          >
            <TypeIcon type={ticket.type} size={13} />
            <TicketKey>{ticket.key}</TicketKey>
            <button type="button" onClick={() => onOpen(ticket.key)}>
              {ticket.title}
            </button>
          </li>
        ))}
      </S.List>
    </S.Panel>
  );
}
