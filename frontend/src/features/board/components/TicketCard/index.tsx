import { CircleSlash, ListChecks } from 'lucide-react';
import { forwardRef } from 'react';
import { useTranslation } from 'react-i18next';
import { PriorityIcon } from '../../../../components/icons/PriorityIcon';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { Avatar } from '../../../../components/ui/Avatar';
import { TicketKey } from '../../../../components/ui/Badge';
import type { TicketSummary } from '../../../../services/api/types';
import * as S from './style';

type Props = React.HTMLAttributes<HTMLDivElement> & {
  ticket: TicketSummary;
  dragging?: boolean;
  overlay?: boolean;
  /** Another card hovers it: it would be ranked right above. */
  dropTarget?: boolean;
};

export const TicketCard = forwardRef<HTMLDivElement, Props>(function TicketCard(
  { ticket, dragging = false, overlay = false, dropTarget = false, ...rest },
  ref,
) {
  const { t } = useTranslation();
  return (
    <S.Card
      ref={ref}
      $draft={ticket.type === 'draft'}
      $dragging={dragging}
      $overlay={overlay}
      $dropTarget={dropTarget}
      aria-label={`${ticket.key} ${ticket.title}`}
      {...rest}
    >
      <S.Top>
        <TypeIcon type={ticket.type} />
        <TicketKey>{ticket.key}</TicketKey>
        <S.Spacer />
        {ticket.blocked && (
          <S.Blocked title={t('ticket.blocked')} aria-label={t('ticket.blocked')}>
            <CircleSlash />
          </S.Blocked>
        )}
        <PriorityIcon priority={ticket.priority} />
      </S.Top>
      <S.Title>{ticket.title}</S.Title>
      <S.Bottom>
        {ticket.tags.slice(0, 3).map((tag) => (
          <S.Tag key={tag}>#{tag}</S.Tag>
        ))}
        <S.Spacer />
        {ticket.checklist_total > 0 && (
          <S.Meta title={t('ticket.checklist')}>
            <ListChecks />
            {ticket.checklist_done}/{ticket.checklist_total}
          </S.Meta>
        )}
        {ticket.assignee && (
          <Avatar
            handle={ticket.assignee.handle}
            name={ticket.assignee.display_name}
            kind={ticket.assignee.kind}
            size={20}
          />
        )}
      </S.Bottom>
    </S.Card>
  );
});
