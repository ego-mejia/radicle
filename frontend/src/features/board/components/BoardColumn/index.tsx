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
}: {
  ticket: TicketSummary;
  onOpen: () => void;
  disabled: boolean;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: ticket.key,
    data: { ticket },
    disabled,
  });
  return (
    <TicketCard
      ref={setNodeRef}
      ticket={ticket}
      dragging={isDragging}
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
  category: Category;
  tickets: TicketSummary[];
  state: 'idle' | 'allowed' | 'blocked';
  canDrag: boolean;
  onOpen: (key: string) => void;
  footer?: React.ReactNode;
};

export function BoardColumn({ category, tickets, state, canDrag, onOpen, footer }: Props) {
  const { t } = useTranslation();
  const { setNodeRef, isOver } = useDroppable({ id: category, disabled: state === 'blocked' });
  const label = t(`ticket.categories.${category}`);
  return (
    <S.Column
      ref={setNodeRef}
      $state={isOver && state === 'allowed' ? 'over' : state}
      aria-label={label}
      data-testid={`column-${category}`}
    >
      <S.Head>
        <CategoryIcon category={category} size={16} />
        <h2>{label}</h2>
        <S.Count>{tickets.length}</S.Count>
      </S.Head>
      <S.Cards>
        {tickets.length === 0 && <S.Empty>{t('board.emptyColumn')}</S.Empty>}
        {tickets.map((ticket) => (
          <DraggableCard
            key={ticket.key}
            ticket={ticket}
            disabled={!canDrag}
            onOpen={() => onOpen(ticket.key)}
          />
        ))}
      </S.Cards>
      {footer && <S.Footer>{footer}</S.Footer>}
    </S.Column>
  );
}
