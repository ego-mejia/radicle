import { useDraggable, useDroppable } from '@dnd-kit/core';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import type { Category, TicketSummary } from '../../../../services/api/types';
import { TicketCard } from '../TicketCard';
import * as S from './style';

function DraggableCard({
  ticket,
  onOpen,
  disabled,
  fields,
}: {
  ticket: TicketSummary;
  onOpen: () => void;
  disabled: boolean;
  fields?: string[];
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: ticket.key,
    data: { ticket },
    disabled,
  });
  // Each card is also a drop target: dropping on a card of the same column ranks above it.
  const drop = useDroppable({ id: `card:${ticket.key}`, data: { ticket }, disabled });
  return (
    <TicketCard
      ref={(node) => {
        setNodeRef(node);
        drop.setNodeRef(node);
      }}
      dropTarget={drop.isOver && !isDragging}
      ticket={ticket}
      fields={fields}
      dragging={isDragging}
      data-nav-item
      {...attributes}
      {...listeners}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onOpen();
        listeners?.onKeyDown?.(e);
      }}
    />
  );
}

type Props = {
  /** Droppable id; the board knows which column (and lane) it is. */
  dropId: string;
  index: number;
  name: string;
  category: Category;
  tickets: TicketSummary[];
  count: number;
  wipLimit?: number | null;
  overLimit?: boolean;
  state: 'idle' | 'allowed' | 'blocked';
  canDrag: boolean;
  onOpen: (key: string) => void;
  fields?: string[];
  footer?: React.ReactNode;
  /** In a swimlane the header is shared, so cells hide it. */
  showHeader?: boolean;
};

export function BoardColumn({
  dropId,
  index,
  name,
  category,
  tickets,
  count,
  wipLimit,
  overLimit = false,
  state,
  canDrag,
  onOpen,
  fields,
  footer,
  showHeader = true,
}: Props) {
  const { t } = useTranslation();
  const { setNodeRef, isOver } = useDroppable({
    id: dropId,
    data: { column: index },
    disabled: state === 'blocked',
  });
  return (
    <S.Column
      ref={setNodeRef}
      $state={isOver && state === 'allowed' ? 'over' : state}
      $over={overLimit}
      aria-label={name}
      data-testid={`column-${category}`}
      data-column={index}
    >
      {showHeader && (
        <S.Head>
          <CategoryIcon category={category} size={14} />
          <h2>{name}</h2>
          <S.Count
            $over={overLimit}
            title={wipLimit ? t('board.wip', { limit: wipLimit }) : undefined}
          >
            {wipLimit ? `${count} / ${wipLimit}` : count}
          </S.Count>
        </S.Head>
      )}
      <S.Cards>
        {tickets.length === 0 && <S.Empty>{t('board.emptyColumn')}</S.Empty>}
        {tickets.map((ticket) => (
          <DraggableCard
            key={ticket.key}
            ticket={ticket}
            fields={fields}
            disabled={!canDrag}
            onOpen={() => onOpen(ticket.key)}
          />
        ))}
      </S.Cards>
      {footer && <S.Footer>{footer}</S.Footer>}
    </S.Column>
  );
}
