import { useQuery } from '@tanstack/react-query';
import { ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { groupTickets, topLevel, type GroupBy } from '../../../../lib/ticketGroups';
import { fetchChildren, ticketKeys } from '../../../../services/api/tickets';
import type { TicketSummary } from '../../../../services/api/types';
import { TicketRow } from '../TicketRow';
import * as S from './style';

type RowProps = {
  ticket: TicketSummary;
  depth: number;
  onOpen: (key: string) => void;
  selected?: Set<string>;
  onSelect?: (keys: string[], selected: boolean) => void;
};

function Children(props: RowProps) {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: ticketKeys.children(props.ticket.key),
    queryFn: () => fetchChildren(props.ticket.key),
  });
  if (!data) {
    return (
      <tr>
        <S.Loading colSpan={99} style={{ paddingLeft: 40 + props.depth * 22 }}>
          {t('common.loading')}
        </S.Loading>
      </tr>
    );
  }
  return (
    <>
      {data.map((child) => (
        <TreeRow key={child.key} {...props} ticket={child} depth={props.depth + 1} />
      ))}
    </>
  );
}

/** A ticket and, once opened, its subtickets (tasks, bugs...) nested below it. */
function TreeRow(props: RowProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const count = props.ticket.child_count ?? 0;
  const expander =
    count > 0 ? (
      <S.Expander
        type="button"
        $open={open}
        aria-expanded={open}
        aria-label={t('list.subtickets', { key: props.ticket.key, count })}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
      >
        <ChevronRight size={14} />
        <span>{count}</span>
      </S.Expander>
    ) : (
      <S.Spacer aria-hidden />
    );
  return (
    <>
      <TicketRow
        ticket={props.ticket}
        onOpen={props.onOpen}
        selected={props.selected}
        onSelect={props.onSelect}
        sortable={false}
        handle={null}
        depth={props.depth}
        expander={expander}
      />
      {open && <Children {...props} />}
    </>
  );
}

type Props = Omit<RowProps, 'ticket' | 'depth'> & {
  tickets: TicketSummary[];
  groupBy: GroupBy;
  nest: boolean;
  columns: number;
};

/** Rows split in collapsible groups, with subtickets nested under their parents. */
export function GroupedRows({ tickets, groupBy, nest, columns, ...row }: Props) {
  const { t } = useTranslation();
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const groups = groupTickets(tickets, groupBy);
  return (
    <tbody>
      {groups.map((group) => {
        const isClosed = closed.has(group.id);
        const rows = nest ? topLevel(group.tickets) : group.tickets;
        return [
          groupBy !== 'none' && (
            <S.GroupRow key={`group:${group.id}`}>
              <td colSpan={columns}>
                <S.GroupToggle
                  type="button"
                  aria-expanded={!isClosed}
                  $open={!isClosed}
                  onClick={() => {
                    const next = new Set(closed);
                    if (isClosed) next.delete(group.id);
                    else next.add(group.id);
                    setClosed(next);
                  }}
                >
                  <ChevronRight size={16} />
                  <strong>
                    {group.label === null
                      ? t(`list.groupNone.${groupBy}`)
                      : groupBy === 'type'
                        ? t(`ticket.types.${group.label}`)
                        : groupBy === 'priority'
                          ? t(`ticket.priorities.${group.label}`)
                          : group.label}
                  </strong>
                  <S.Count>{group.tickets.length}</S.Count>
                </S.GroupToggle>
              </td>
            </S.GroupRow>
          ),
          ...(isClosed
            ? []
            : rows.map((ticket) => (
                <TreeRow key={ticket.key} ticket={ticket} depth={0} {...row} />
              ))),
        ];
      })}
    </tbody>
  );
}
