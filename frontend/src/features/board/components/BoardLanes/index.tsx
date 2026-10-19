import { ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { columnCategory } from '../../../../lib/boards';
import type { BoardData } from '../../../../services/api/types';
import { BoardColumn } from '../BoardColumn';
import * as S from './style';

type Props = {
  data: BoardData;
  columnState: (index: number) => 'idle' | 'allowed' | 'blocked';
  canDrag: boolean;
  onOpen: (key: string) => void;
};

/** Columns split into collapsible rows by the swimlane value. */
export function BoardLanes({ data, columnState, canDrag, onOpen }: Props) {
  const { t } = useTranslation();
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const columns = data.columns;
  const template = `repeat(${columns.length}, minmax(240px, 1fr))`;
  const toggle = (key: string) =>
    setClosed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  return (
    <S.Wrapper>
      <S.Header style={{ gridTemplateColumns: template }}>
        {columns.map((c) => (
          <S.ColumnHead key={c.index} $over={c.over_limit}>
            <CategoryIcon
              category={columnCategory(data.board, data.board.columns[c.index]!)}
              size={16}
            />
            <span>{c.name}</span>
            <small>{c.wip_limit ? `${c.count} / ${c.wip_limit}` : c.count}</small>
          </S.ColumnHead>
        ))}
      </S.Header>
      {data.lanes.map((lane) => {
        const open = !closed.has(lane.key);
        return (
          <S.Lane key={lane.key || 'none'}>
            <S.LaneHead type="button" aria-expanded={open} onClick={() => toggle(lane.key)}>
              {open ? <ChevronDown /> : <ChevronRight />}
              {lane.label || t(`board.noLane.${data.swimlane_by}`)}
              <small>{lane.count}</small>
            </S.LaneHead>
            {open && (
              <S.Row style={{ gridTemplateColumns: template }}>
                {columns.map((c) => {
                  const tickets = c.tickets.filter((ticket) => ticket.lane === lane.key);
                  return (
                    <BoardColumn
                      key={c.index}
                      dropId={`col:${c.index}:${lane.key}`}
                      index={c.index}
                      name={c.name}
                      category={columnCategory(data.board, data.board.columns[c.index]!)}
                      tickets={tickets}
                      count={tickets.length}
                      state={columnState(c.index)}
                      canDrag={canDrag}
                      onOpen={onOpen}
                      fields={data.board.card_fields}
                      showHeader={false}
                    />
                  );
                })}
              </S.Row>
            )}
          </S.Lane>
        );
      })}
    </S.Wrapper>
  );
}
