import { useDroppable } from '@dnd-kit/core';
import { Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { formatHours } from '../../../../lib/duration';
import { formatDate } from '../../../../lib/format';
import type { Sprint, TicketSummary } from '../../../../services/api/types';
import { BacklogRow } from '../BacklogRow';
import * as S from './style';

type Props = {
  /** A sprint, or null for the backlog list. */
  sprint: Sprint | null;
  tickets: TicketSummary[];
  total?: number;
  selected: Set<string>;
  canEdit: boolean;
  isAdmin: boolean;
  canStart: boolean;
  onSelect: (key: string, selected: boolean) => void;
  onOpen: (key: string) => void;
  onStart?: () => void;
  onComplete?: () => void;
  onDelete?: () => void;
};

/** A sprint (or the backlog) as a drop target with its tickets, hours and capacity. */
export function SprintSection({
  sprint,
  tickets,
  total,
  selected,
  canEdit,
  isAdmin,
  canStart,
  onSelect,
  onOpen,
  onStart,
  onComplete,
  onDelete,
}: Props) {
  const { t } = useTranslation();
  const id = sprint?.id ?? 'backlog';
  const { setNodeRef, isOver } = useDroppable({ id: `list:${id}`, data: { list: id } });
  const capacity = sprint?.capacity_hours ?? null;
  const hours = sprint
    ? sprint.estimate_hours
    : tickets.reduce((sum, ticket) => sum + (ticket.estimate_hours ?? 0), 0);
  const name = sprint?.name ?? t('sprints.backlog');
  return (
    <S.Section aria-label={name} data-testid={`list-${sprint ? sprint.name : 'backlog'}`}>
      <S.Head>
        <h2>{name}</h2>
        {sprint && (
          <Badge tone={sprint.state === 'active' ? 'accent' : 'neutral'}>
            {t(`sprints.states.${sprint.state}`)}
          </Badge>
        )}
        {sprint?.start_date && (
          <S.Muted>
            {formatDate(sprint.start_date)} – {formatDate(sprint.end_date)}
          </S.Muted>
        )}
        <S.Muted>
          {t('sprints.summary', { count: total ?? tickets.length, hours: formatHours(hours) })}
        </S.Muted>
        <S.Spacer />
        {isAdmin && sprint?.state === 'future' && (
          <>
            <Button size="sm" variant="primary" disabled={!canStart} onClick={onStart}>
              {t('sprints.start')}
            </Button>
            <IconButton label={t('sprints.delete', { name })} onClick={onDelete}>
              <Trash2 />
            </IconButton>
          </>
        )}
        {isAdmin && sprint?.state === 'active' && (
          <Button size="sm" variant="primary" onClick={onComplete}>
            {t('sprints.complete')}
          </Button>
        )}
      </S.Head>
      {sprint?.goal && <S.Goal>{sprint.goal}</S.Goal>}
      {capacity != null && (
        <S.Capacity
          role="meter"
          aria-label={t('sprints.capacity')}
          aria-valuemin={0}
          aria-valuemax={capacity}
          aria-valuenow={hours}
          $over={hours > capacity}
        >
          <S.Bar
            $over={hours > capacity}
            style={{ width: `${Math.min(100, (hours / Math.max(capacity, 1)) * 100)}%` }}
          />
          <span>
            {t('sprints.capacityOf', {
              hours: formatHours(hours),
              capacity: formatHours(capacity),
            })}
          </span>
        </S.Capacity>
      )}
      {sprint && sprint.unestimated_count > 0 && (
        <S.Warning>{t('sprints.unestimated', { count: sprint.unestimated_count })}</S.Warning>
      )}
      <S.List ref={setNodeRef} $over={isOver}>
        {tickets.length === 0 && (
          <S.Empty>{sprint ? t('sprints.emptySprint') : t('sprints.emptyBacklog')}</S.Empty>
        )}
        {tickets.map((ticket) => (
          <BacklogRow
            key={ticket.key}
            ticket={ticket}
            from={id}
            selected={selected.has(ticket.key)}
            canEdit={canEdit}
            onSelect={(value) => onSelect(ticket.key, value)}
            onOpen={() => onOpen(ticket.key)}
          />
        ))}
      </S.List>
    </S.Section>
  );
}
