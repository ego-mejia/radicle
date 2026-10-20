import { ChevronRight, ChevronsDownUp, ChevronsUpDown } from 'lucide-react';
import { useEffect, useState } from 'react';
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

const storageKey = (data: BoardData) => `radicle.lanes.${data.board.id}.${data.swimlane_by}`;

function readClosed(key: string): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(key) ?? '[]') as string[]);
  } catch {
    return new Set();
  }
}

/** Columns split into collapsible rows (one small board per area, assignee...). */
export function BoardLanes({ data, columnState, canDrag, onOpen }: Props) {
  const { t } = useTranslation();
  const key = storageKey(data);
  const [closed, setClosed] = useState<Set<string>>(() => readClosed(key));
  useEffect(() => setClosed(readClosed(key)), [key]);
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify([...closed]));
    } catch {
      // private mode: lanes just reopen next time
    }
  }, [key, closed]);
  const allClosed = data.lanes.length > 0 && data.lanes.every((l) => closed.has(l.key));
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
      <S.Tools>
        <S.ToggleAll
          type="button"
          onClick={() => setClosed(allClosed ? new Set() : new Set(data.lanes.map((l) => l.key)))}
        >
          {allClosed ? <ChevronsUpDown /> : <ChevronsDownUp />}
          {allClosed ? t('board.expandAll') : t('board.collapseAll')}
        </S.ToggleAll>
      </S.Tools>
      <S.Header style={{ gridTemplateColumns: template }}>
        {columns.map((c) => (
          <S.ColumnHead key={c.index} $over={c.over_limit}>
            <CategoryIcon
              category={columnCategory(data.board, data.board.columns[c.index]!)}
              size={14}
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
            <S.LaneHead
              type="button"
              aria-expanded={open}
              $open={open}
              onClick={() => toggle(lane.key)}
            >
              <ChevronRight />
              <strong>{lane.label || t(`board.noLane.${data.swimlane_by}`)}</strong>
              <small>{t('board.laneCount', { count: lane.count })}</small>
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
