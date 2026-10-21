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
import type { DbColumn, DbRow } from '../../../../../../services/api/folioDatabases';
import { Choice } from '../../../DbValue';
import { RowCard } from '../CardsView';
import { dropFor, groupsOf, NONE } from './board';
import * as S from './style';

type Props = {
  /** The select column the board groups by. */
  group: DbColumn;
  columns: DbColumn[];
  rows: DbRow[];
  /** Dropping a card in another group sets its value; without it the cards stay put. */
  onMove?: (row: DbRow, value: string | null) => void;
};

function Card({ columns, row, canMove }: { columns: DbColumn[]; row: DbRow; canMove: boolean }) {
  const drag = useDraggable({ id: row.id, disabled: !canMove });
  return (
    <S.Card
      ref={drag.setNodeRef}
      $dragging={drag.isDragging}
      style={
        drag.transform
          ? { transform: `translate(${drag.transform.x}px, ${drag.transform.y}px)` }
          : undefined
      }
      {...(canMove ? { ...drag.listeners, ...drag.attributes } : {})}
    >
      <RowCard columns={columns} row={row} />
    </S.Card>
  );
}

function Group({
  children,
  value,
  label,
}: {
  children: React.ReactNode;
  value: string;
  label: React.ReactNode;
}) {
  const drop = useDroppable({ id: value });
  return (
    <S.Group ref={drop.setNodeRef} $over={drop.isOver}>
      {label}
      <S.Cards>{children}</S.Cards>
    </S.Group>
  );
}

/** Rows as a board grouped by a select column; dragging a card between groups changes it. */
export function BoardView({ group, columns, rows, onMove }: Props) {
  const { t } = useTranslation();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor),
  );
  const shown = columns.filter((c) => c.key !== group.key);
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || !onMove) return;
    const move = dropFor(group, rows, String(active.id), String(over.id));
    if (move) onMove(move.row, move.value);
  };

  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <S.Board aria-label={t('folio.db.board', { column: group.name })}>
        {groupsOf(group, rows).map((g) => (
          <Group
            key={g.value}
            value={g.value}
            label={
              <S.Label>
                {g.value === NONE ? (
                  t('folio.db.noValue')
                ) : (
                  <Choice column={group} value={g.value} />
                )}
                <span>{g.rows.length}</span>
              </S.Label>
            }
          >
            {g.rows.map((row) => (
              <Card key={row.id} columns={shown} row={row} canMove={!!onMove} />
            ))}
          </Group>
        ))}
      </S.Board>
    </DndContext>
  );
}
