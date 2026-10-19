import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { useTranslation } from 'react-i18next';
import { dotSize, quadrant } from '../../../../lib/inbox';
import type { TicketSummary } from '../../../../services/api/types';
import * as S from './style';

const LEVELS = [1, 2, 3, 4, 5];

function Dot({ ticket, disabled }: { ticket: TicketSummary; disabled: boolean }) {
  const { t } = useTranslation();
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: ticket.key,
    data: { ticket },
    disabled,
  });
  const size = dotSize(ticket.vote_count);
  return (
    <S.Dot
      ref={setNodeRef}
      type="button"
      $kind={ticket.classification ?? 'idea'}
      $dragging={isDragging}
      style={{ width: size, height: size }}
      aria-label={t('inbox.dot', {
        key: ticket.key,
        title: ticket.title,
        votes: ticket.vote_count,
      })}
      title={`${ticket.key} ${ticket.title} · 🙋 ${ticket.vote_count}`}
      data-testid={`dot-${ticket.key}`}
      {...attributes}
      {...listeners}
    />
  );
}

function Cell({
  impact,
  effort,
  items,
  disabled,
}: {
  impact: number;
  effort: number;
  items: TicketSummary[];
  disabled: boolean;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `cell:${impact}:${effort}`,
    data: { impact, effort },
  });
  return (
    <S.Cell
      ref={setNodeRef}
      $quadrant={quadrant(impact, effort)}
      $over={isOver}
      style={{ gridRow: LEVELS.length + 1 - impact, gridColumn: effort }}
      data-testid={`cell-${impact}-${effort}`}
    >
      {items.map((ticket) => (
        <Dot key={ticket.key} ticket={ticket} disabled={disabled} />
      ))}
    </S.Cell>
  );
}

type Props = {
  items: TicketSummary[];
  canTriage: boolean;
  onScore: (key: string, impact: number, effort: number) => void;
};

/** Impact (up) by effort (right). Drag a dot to rescore it; unscored ones wait on the side. */
export function ImpactMatrix({ items, canTriage, onScore }: Props) {
  const { t } = useTranslation();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor),
  );
  const scored = items.filter((i) => i.impact != null && i.effort != null);
  const unscored = items.filter((i) => i.impact == null || i.effort == null);
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    const target = over?.data.current as { impact: number; effort: number } | undefined;
    const ticket = active.data.current?.ticket as TicketSummary | undefined;
    if (!target || !ticket) return;
    if (ticket.impact === target.impact && ticket.effort === target.effort) return;
    onScore(ticket.key, target.impact, target.effort);
  };
  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <S.Wrap>
        <S.Matrix role="group" aria-label={t('inbox.matrix')}>
          <S.AxisY>{t('inbox.impact')} ↑</S.AxisY>
          <S.Grid>
            {[...LEVELS]
              .reverse()
              .map((impact) =>
                LEVELS.map((effort) => (
                  <Cell
                    key={`${impact}-${effort}`}
                    impact={impact}
                    effort={effort}
                    disabled={!canTriage}
                    items={scored.filter((i) => i.impact === impact && i.effort === effort)}
                  />
                )),
              )}
            <S.Label style={{ gridArea: '1 / 1 / 3 / 3' }}>
              {t('inbox.quadrants.quick_wins')}
            </S.Label>
            <S.Label style={{ gridArea: '1 / 4 / 3 / 6' }}>{t('inbox.quadrants.big_bets')}</S.Label>
            <S.Label style={{ gridArea: '4 / 1 / 6 / 3' }}>{t('inbox.quadrants.fillers')}</S.Label>
            <S.Label style={{ gridArea: '4 / 4 / 6 / 6' }}>
              {t('inbox.quadrants.not_worth')}
            </S.Label>
          </S.Grid>
          <S.AxisX>{t('inbox.effort')} →</S.AxisX>
        </S.Matrix>
        <S.Side aria-label={t('inbox.unscored')}>
          <h3>{t('inbox.unscored')}</h3>
          {unscored.length === 0 && <p>{t('inbox.allScored')}</p>}
          {unscored.map((ticket) => (
            <S.Unscored key={ticket.key}>
              <Dot ticket={ticket} disabled={!canTriage} />
              <span>
                <b>{ticket.key}</b> {ticket.title}
              </span>
            </S.Unscored>
          ))}
        </S.Side>
      </S.Wrap>
    </DndContext>
  );
}
