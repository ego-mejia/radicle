import { ArrowDown, ArrowUp, CircleSlash } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { formatDate, isOverdue, relativeTime } from '../../lib/format';
import type { TicketSummary } from '../../services/api/types';
import { CategoryIcon } from '../icons/CategoryIcon';
import { PriorityIcon } from '../icons/PriorityIcon';
import { TypeIcon } from '../icons/TypeIcon';
import { Avatar } from '../ui/Avatar';
import { TicketKey } from '../ui/Badge';
import { Spinner } from '../ui/Spinner';
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
          {tickets.map((ticket) => (
            <tr
              key={ticket.key}
              tabIndex={0}
              onClick={() => onOpen(ticket.key)}
              onKeyDown={(e) => e.key === 'Enter' && onOpen(ticket.key)}
              aria-selected={selected?.has(ticket.key) || undefined}
            >
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
                  <S.Muted
                    $danger={isOverdue(ticket.due_date) && ticket.status.category !== 'done'}
                  >
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
          ))}
        </tbody>
      </S.Table>
      <S.Sentinel ref={sentinel} />
      <S.Footer>
        {loadingMore ? <Spinner /> : t('list.showing', { shown: tickets.length, total })}
      </S.Footer>
    </S.Scroller>
  );
}
