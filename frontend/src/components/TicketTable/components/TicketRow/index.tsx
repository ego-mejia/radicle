import { DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { CircleSlash, GripVertical } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatDate, isOverdue, relativeTime } from '../../../../lib/format';
import type { TicketSummary } from '../../../../services/api/types';
import { CategoryIcon } from '../../../icons/CategoryIcon';
import { PriorityIcon } from '../../../icons/PriorityIcon';
import { TypeIcon } from '../../../icons/TypeIcon';
import { Avatar } from '../../../ui/Avatar';
import { TicketKey } from '../../../ui/Badge';
import * as S from '../../style';

type Handle = ReturnType<typeof useSortable> | null;

type RowsProps = {
  tickets: TicketSummary[];
  onReorder?: (key: string, place: { before?: string; after?: string }) => Promise<void>;
  children: (ticket: TicketSummary, handle: Handle) => React.ReactNode;
};

/** The table body; with `onReorder` its rows can be dragged to change the rank. */
export function Rows({ tickets, onReorder, children }: RowsProps) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));
  if (!onReorder) return <tbody>{tickets.map((t) => children(t, null))}</tbody>;
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const from = tickets.findIndex((t) => t.key === active.id);
    const to = tickets.findIndex((t) => t.key === over.id);
    void onReorder(
      String(active.id),
      to < from ? { before: String(over.id) } : { after: String(over.id) },
    );
  };
  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <SortableContext items={tickets.map((t) => t.key)} strategy={verticalListSortingStrategy}>
        <tbody>
          {tickets.map((t) => (
            <SortableRow key={t.key} id={t.key}>
              {(handle) => children(t, handle)}
            </SortableRow>
          ))}
        </tbody>
      </SortableContext>
    </DndContext>
  );
}

function SortableRow({ id, children }: { id: string; children: (h: Handle) => React.ReactNode }) {
  const handle = useSortable({ id });
  return <>{children(handle)}</>;
}

type Props = {
  ticket: TicketSummary;
  onOpen: (key: string) => void;
  selected?: Set<string>;
  onSelect?: (keys: string[], selected: boolean) => void;
  sortable: boolean;
  handle: Handle;
};

export function TicketRow({ ticket, onOpen, selected, onSelect, sortable, handle }: Props) {
  const { t } = useTranslation();
  return (
    <tr
      ref={handle?.setNodeRef}
      style={
        handle
          ? {
              transform: CSS.Translate.toString(handle.transform),
              transition: handle.transition,
            }
          : undefined
      }
      tabIndex={0}
      data-nav-item
      onClick={() => onOpen(ticket.key)}
      onKeyDown={(e) => e.key === 'Enter' && onOpen(ticket.key)}
      aria-selected={selected?.has(ticket.key) || undefined}
    >
      {sortable && (
        <S.CheckCell onClick={(e) => e.stopPropagation()}>
          <S.Grip
            {...handle?.attributes}
            {...handle?.listeners}
            aria-label={t('rank.drag', { key: ticket.key })}
          >
            <GripVertical size={14} />
          </S.Grip>
        </S.CheckCell>
      )}
      {selected && onSelect && (
        <S.CheckCell onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            aria-label={t('bulk.select', { key: ticket.key })}
            checked={selected.has(ticket.key)}
            onChange={(e) => onSelect([ticket.key], e.target.checked)}
          />
        </S.CheckCell>
      )}
      <td>
        <TicketKey>{ticket.key}</TicketKey>
      </td>
      <td>
        <TypeIcon type={ticket.type} />
      </td>
      <S.TitleCell>
        <S.Cell>
          {ticket.blocked && (
            <S.Muted $danger title={t('ticket.blocked')}>
              <CircleSlash size={13} />
            </S.Muted>
          )}
          {ticket.title}
        </S.Cell>
      </S.TitleCell>
      <td>
        <S.Cell>
          <CategoryIcon category={ticket.status.category} />
          {ticket.status.name}
        </S.Cell>
      </td>
      <td>
        <S.Cell>
          <PriorityIcon priority={ticket.priority} />
          {t(`ticket.priorities.${ticket.priority}`)}
        </S.Cell>
      </td>
      <td>
        {ticket.vote_count > 0 ? (
          <S.Cell title={t('votes.count', { count: ticket.vote_count })}>
            🙋 {ticket.vote_count}
          </S.Cell>
        ) : (
          <S.Muted>—</S.Muted>
        )}
      </td>
      <td>
        {ticket.assignee ? (
          <S.Cell>
            <Avatar
              handle={ticket.assignee.handle}
              name={ticket.assignee.display_name}
              kind={ticket.assignee.kind}
              size={20}
            />
            {ticket.assignee.handle}
          </S.Cell>
        ) : (
          <S.Muted>—</S.Muted>
        )}
      </td>
      <td>{ticket.area ?? <S.Muted>—</S.Muted>}</td>
      <td>{ticket.milestone ?? <S.Muted>—</S.Muted>}</td>
      <td>
        {ticket.due_date ? (
          <S.Muted $danger={isOverdue(ticket.due_date) && ticket.status.category !== 'done'}>
            {formatDate(ticket.due_date)}
          </S.Muted>
        ) : (
          <S.Muted>—</S.Muted>
        )}
      </td>
      <td>
        <S.Muted>{relativeTime(ticket.updated_at)}</S.Muted>
      </td>
    </tr>
  );
}
