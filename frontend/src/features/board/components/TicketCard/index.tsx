import { CalendarDays, CircleSlash, Clock, ListChecks } from 'lucide-react';
import { forwardRef } from 'react';
import { useTranslation } from 'react-i18next';
import { PriorityIcon } from '../../../../components/icons/PriorityIcon';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { Avatar } from '../../../../components/ui/Avatar';
import { formatHours } from '../../../../lib/duration';
import { formatDate, isOverdue } from '../../../../lib/format';
import type { TicketSummary } from '../../../../services/api/types';
import * as S from './style';

const DEFAULT_CARD_FIELDS = ['priority', 'assignee', 'tags', 'checklist'];

type Props = React.HTMLAttributes<HTMLDivElement> & {
  ticket: TicketSummary;
  dragging?: boolean;
  overlay?: boolean;
  /** Another card hovers it: it would be ranked right above. */
  dropTarget?: boolean;
  /** It just moved: a short flash, brighter when it landed in a done column. */
  flash?: 'moved' | 'done';
  /** Optional fields the board shows; key, title and type always show. */
  fields?: string[];
};

export const TicketCard = forwardRef<HTMLDivElement, Props>(function TicketCard(
  {
    ticket,
    dragging = false,
    overlay = false,
    dropTarget = false,
    flash,
    fields = DEFAULT_CARD_FIELDS,
    ...rest
  },
  ref,
) {
  const { t } = useTranslation();
  const show = (name: string) => fields.includes(name);
  const custom = fields.filter((f) => f.startsWith('cf.'));
  return (
    <S.Card
      ref={ref}
      $draft={ticket.type === 'draft'}
      $dragging={dragging}
      $overlay={overlay}
      $dropTarget={dropTarget}
      $flash={flash}
      data-flash={flash}
      aria-label={`${ticket.key} ${ticket.title}`}
      {...rest}
    >
      <S.Title>{ticket.title}</S.Title>
      {(show('tags') && ticket.tags.length > 0) || custom.length > 0 ? (
        <S.Labels>
          {show('tags') && ticket.tags.slice(0, 3).map((tag) => <S.Tag key={tag}>{tag}</S.Tag>)}
          {custom.map((name) => {
            const value = ticket.custom_fields?.[name.slice(3)];
            return value === undefined || value === null ? null : (
              <S.Meta key={name}>
                {name.slice(3)}: {String(value)}
              </S.Meta>
            );
          })}
        </S.Labels>
      ) : null}
      <S.Bottom>
        <TypeIcon type={ticket.type} />
        <S.Key $done={ticket.status.category === 'done'}>{ticket.key}</S.Key>
        {ticket.blocked && (
          <S.Blocked title={t('ticket.blocked')} aria-label={t('ticket.blocked')}>
            <CircleSlash />
          </S.Blocked>
        )}
        <S.Spacer />
        {show('due') && ticket.due_date && (
          <S.Pill
            $danger={isOverdue(ticket.due_date) && ticket.status.category !== 'done'}
            title={t('ticket.fields.due')}
          >
            <CalendarDays />
            {formatDate(ticket.due_date)}
          </S.Pill>
        )}
        {show('checklist') && ticket.checklist_total > 0 && (
          <S.Meta title={t('ticket.checklist')}>
            <ListChecks />
            {ticket.checklist_done}/{ticket.checklist_total}
          </S.Meta>
        )}
        {show('votes') && ticket.vote_count > 0 && (
          <S.Meta title={t('votes.count', { count: ticket.vote_count })}>
            🙋 {ticket.vote_count}
          </S.Meta>
        )}
        {show('estimate') && ticket.estimate_hours !== null && (
          <S.Pill title={t('ticket.fields.estimate')}>
            <Clock />
            {formatHours(ticket.estimate_hours)}
          </S.Pill>
        )}
        {show('remaining') && ticket.estimate_hours !== null && (
          <S.Pill title={t('time.remaining')}>
            {formatHours(Math.max(ticket.estimate_hours - ticket.spent_hours, 0))}
          </S.Pill>
        )}
        {show('priority') && <PriorityIcon priority={ticket.priority} />}
        {show('assignee') && ticket.assignee && (
          <Avatar
            handle={ticket.assignee.handle}
            name={ticket.assignee.display_name}
            kind={ticket.assignee.kind}
            size={24}
          />
        )}
      </S.Bottom>
    </S.Card>
  );
});
