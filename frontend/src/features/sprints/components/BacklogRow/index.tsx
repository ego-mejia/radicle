import { useDraggable } from '@dnd-kit/core';
import { AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { PriorityIcon } from '../../../../components/icons/PriorityIcon';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { Avatar } from '../../../../components/ui/Avatar';
import { TicketKey } from '../../../../components/ui/Badge';
import { formatHours } from '../../../../lib/duration';
import type { TicketSummary } from '../../../../services/api/types';
import * as S from './style';

type Props = {
  ticket: TicketSummary;
  /** Where it sits now: a sprint id or 'backlog'. */
  from: string;
  selected: boolean;
  canEdit: boolean;
  onSelect: (selected: boolean) => void;
  onOpen: () => void;
};

/** One ticket in the backlog or a sprint; drag it to another list. */
export function BacklogRow({ ticket, from, selected, canEdit, onSelect, onOpen }: Props) {
  const { t } = useTranslation();
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `${from}:${ticket.key}`,
    data: { key: ticket.key, from },
    disabled: !canEdit,
  });
  return (
    <S.Row ref={setNodeRef} $dragging={isDragging} $selected={selected} data-nav-item>
      {canEdit && (
        <input
          type="checkbox"
          aria-label={t('sprints.select', { key: ticket.key })}
          checked={selected}
          onChange={(e) => onSelect(e.target.checked)}
        />
      )}
      <S.Handle {...attributes} {...listeners} aria-label={t('sprints.drag', { key: ticket.key })}>
        <TypeIcon type={ticket.type} size={14} />
        <TicketKey>{ticket.key}</TicketKey>
      </S.Handle>
      <S.Title type="button" onClick={onOpen}>
        {ticket.title}
      </S.Title>
      <CategoryIcon category={ticket.status.category} size={14} />
      <S.Status>{ticket.status.name}</S.Status>
      <PriorityIcon priority={ticket.priority} size={14} />
      <S.Hours>
        {ticket.estimate_hours == null ? (
          <S.Missing title={t('sprints.noEstimate')}>
            <AlertTriangle size={13} aria-hidden />
            {t('sprints.noEstimateShort')}
          </S.Missing>
        ) : (
          formatHours(ticket.estimate_hours)
        )}
      </S.Hours>
      {ticket.assignee ? (
        <Avatar
          handle={ticket.assignee.handle}
          name={ticket.assignee.display_name}
          kind={ticket.assignee.kind}
          size={20}
        />
      ) : (
        <S.Empty />
      )}
    </S.Row>
  );
}
