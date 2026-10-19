import { ArrowDown, ArrowUp } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { TicketSummary } from '../../services/api/types';
import { Spinner } from '../ui/Spinner';
import { Rows, TicketRow } from './components/TicketRow';
import * as S from './style';

type Sort = { field: string; desc: boolean } | null;

type Props = {
  tickets: TicketSummary[];
  total: number;
  onOpen: (key: string) => void;
  sort?: Sort;
  onSort?: (field: string) => void;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  /** With a selection, each row gets a checkbox for bulk actions. */
  selected?: Set<string>;
  onSelect?: (keys: string[], selected: boolean) => void;
  /** When ordered by rank: drag rows to reorder. */
  onReorder?: (key: string, place: { before?: string; after?: string }) => Promise<void>;
};

const COLUMNS: { id: string; sort?: string }[] = [
  { id: 'key', sort: 'key' },
  { id: 'type' },
  { id: 'title' },
  { id: 'status', sort: 'status' },
  { id: 'priority', sort: 'priority' },
  { id: 'votes', sort: 'votes' },
  { id: 'assignee' },
  { id: 'area' },
  { id: 'milestone' },
  { id: 'due', sort: 'due' },
  { id: 'updated', sort: 'updated' },
];

/** Ticket rows with sortable headers and infinite scroll. */
export function TicketTable({
  tickets,
  total,
  onOpen,
  sort,
  onSort,
  hasMore,
  loadingMore,
  onLoadMore,
  selected,
  onSelect,
  onReorder,
}: Props) {
  const { t } = useTranslation();
  const sentinel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = sentinel.current;
    if (!node || !hasMore || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) onLoadMore();
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, onLoadMore]);

  return (
    <S.Scroller>
      <S.Table>
        <thead>
          <tr>
            {onReorder && <S.CheckCell aria-hidden />}
            {selected && onSelect && (
              <S.CheckCell>
                <input
                  type="checkbox"
                  aria-label={t('bulk.selectAll')}
                  checked={tickets.length > 0 && tickets.every((x) => selected.has(x.key))}
                  onChange={(e) =>
                    onSelect(
                      tickets.map((x) => x.key),
                      e.target.checked,
                    )
                  }
                />
              </S.CheckCell>
            )}
            {COLUMNS.map((col) => {
              const label = t(`ticket.fields.${col.id}`);
              const sorted = sort?.field === col.sort;
              return (
                <th
                  key={col.id}
                  aria-sort={sorted ? (sort?.desc ? 'descending' : 'ascending') : undefined}
                >
                  {col.sort && onSort ? (
                    <S.SortButton onClick={() => onSort(col.sort!)}>
                      {label}
                      {sorted && (sort?.desc ? <ArrowDown /> : <ArrowUp />)}
                    </S.SortButton>
                  ) : (
                    label
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          <Rows tickets={tickets} onReorder={onReorder}>
            {(ticket, handle) => (
              <TicketRow
                key={ticket.key}
                ticket={ticket}
                onOpen={onOpen}
                selected={selected}
                onSelect={onSelect}
                sortable={Boolean(onReorder)}
                handle={handle}
              />
            )}
          </Rows>
        </tbody>
      </S.Table>
      <S.Sentinel ref={sentinel} />
      <S.Footer>
        {loadingMore ? <Spinner /> : t('list.showing', { shown: tickets.length, total })}
      </S.Footer>
    </S.Scroller>
  );
}
