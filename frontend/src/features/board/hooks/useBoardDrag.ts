import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { optionsFor } from '../../../lib/boards';
import { moveCard, type CardMove } from '../../../services/api/boards';
import { projectKeys } from '../../../services/api/projects';
import { fetchTransitions, ticketKeys } from '../../../services/api/tickets';
import type { BoardCard, BoardData, TransitionOption } from '../../../services/api/types';
import { useMoveFeedback } from '../../tickets/hooks/useMoveFeedback';

type Drag = { ticket: BoardCard; from: number; options: TransitionOption[] | null };

/** Above or below the card under the pointer (by its middle), or last in an empty spot. */
function dropPlace(
  data: BoardData,
  event: DragEndEvent,
  column: number,
  dragged: string,
  over: BoardCard | undefined,
): { before: string | null; after: string | null } {
  if (over && over.key !== dragged) {
    const rect = event.over!.rect;
    const moved = event.active.rect.current.translated;
    const y = moved ? moved.top + moved.height / 2 : rect.top;
    return y < rect.top + rect.height / 2
      ? { before: over.key, after: null }
      : { before: null, after: over.key };
  }
  const rest = data.columns[column]?.tickets.filter((t) => t.key !== dragged) ?? [];
  return { before: null, after: rest.at(-1)?.key ?? null };
}
export type PendingDrop = {
  ticket: BoardCard;
  column: number;
  options: TransitionOption[];
  place: Place;
};
type Place = { before: string | null; after: string | null };

function columnOf(data: BoardData, key: string): number {
  return data.columns.find((c) => c.tickets.some((t) => t.key === key))?.index ?? -1;
}

/** The board right after a move, so the card lands where it was dropped at once. */
export function placeCard(data: BoardData, key: string, column: number, place: Place): BoardData {
  const card = data.columns.flatMap((c) => c.tickets).find((t) => t.key === key);
  if (!card) return data;
  return {
    ...data,
    columns: data.columns.map((c) => {
      const had = c.tickets.some((t) => t.key === key);
      let tickets = c.tickets.filter((t) => t.key !== key);
      if (c.index === column) {
        let at = tickets.length;
        if (place.before)
          at = Math.max(
            0,
            tickets.findIndex((t) => t.key === place.before),
          );
        else if (place.after) at = tickets.findIndex((t) => t.key === place.after) + 1 || at;
        tickets = [...tickets.slice(0, at), card, ...tickets.slice(at)];
      }
      const count = c.count + (c.index === column ? 1 : 0) - (had ? 1 : 0);
      return { ...c, tickets, count };
    }),
  };
}

/** Drag and drop on a board: rank inside a column, move across columns through the API. */
export function useBoardDrag(
  data: BoardData | undefined,
  project: string,
  queryKey: readonly unknown[],
) {
  const queryClient = useQueryClient();
  const feedback = useMoveFeedback();
  const [drag, setDrag] = useState<Drag | null>(null);
  const [pending, setPending] = useState<PendingDrop | null>(null);
  // The transitions request of the current drag: a quick drop waits for it.
  const request = useRef<Promise<TransitionOption[]> | null>(null);
  // The board before a cross-column drop: the card shows in its new column at once and
  // goes back here if the move is not allowed or its dialog is cancelled.
  const before = useRef<BoardData | undefined>(undefined);
  const restore = () => {
    if (before.current) queryClient.setQueryData(queryKey, before.current);
    before.current = undefined;
  };
  const boardId = data?.board.id ?? '';

  const move = useMutation({
    mutationFn: (body: CardMove) => moveCard(boardId, body),
    onMutate: async (body) => {
      // Show the move right away; the server's answer (or an error) settles it.
      await queryClient.cancelQueries({ queryKey });
      queryClient.setQueryData<BoardData>(queryKey, (old) =>
        old
          ? placeCard(old, body.ticket, body.column, {
              before: body.before ?? null,
              after: body.after ?? null,
            })
          : old,
      );
    },
    onSuccess: (out) => feedback.warnings({ ...out.ticket, warnings: out.warnings } as never),
    onError: (error, body) => feedback.error(error, () => move.mutate({ ...body, force: true })),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ticketKeys.all });
      void queryClient.invalidateQueries({ queryKey: projectKeys.detail(project) });
    },
  });

  const onDragStart = async (event: DragStartEvent) => {
    if (!data) return;
    const ticket = event.active.data.current?.ticket as BoardCard;
    setDrag({ ticket, from: columnOf(data, ticket.key), options: null });
    request.current = queryClient.fetchQuery({
      queryKey: [...ticketKeys.transitions(ticket.key), 'drag'],
      queryFn: () => fetchTransitions(ticket.key),
      staleTime: 0,
    });
    const options = await request.current;
    setDrag((cur) => (cur?.ticket.key === ticket.key ? { ...cur, options } : cur));
  };

  const onDragEnd = async (event: DragEndEvent) => {
    const current = drag;
    setDrag(null);
    if (!current || !data) return;
    const overTicket = event.over?.data.current?.ticket as BoardCard | undefined;
    const target = overTicket
      ? columnOf(data, overTicket.key)
      : (event.over?.data.current?.column as number | undefined);
    if (target === undefined || target < 0) return;
    const place = dropPlace(data, event, target, current.ticket.key, overTicket);
    if (target === current.from) {
      if (place.before || place.after)
        move.mutate({ ticket: current.ticket.key, column: target, ...place });
      return;
    }
    before.current = queryClient.getQueryData<BoardData>(queryKey);
    queryClient.setQueryData<BoardData>(queryKey, (old) =>
      old ? placeCard(old, current.ticket.key, target, place) : old,
    );
    const loaded = current.options ?? (await request.current?.catch(() => null));
    const options = loaded ? optionsFor(data.board, target, loaded, current.ticket.type) : [];
    if (options.length === 0) return restore();
    const only = options[0]!;
    const resolutions = only.allowed_resolutions ?? [];
    const simple = only.available && !only.requires_comment && !only.has_screen;
    if (options.length === 1 && simple && (only.category !== 'done' || resolutions.length <= 1)) {
      before.current = undefined;
      move.mutate({
        ticket: current.ticket.key,
        column: target,
        ...place,
        transition: only.name,
        resolution: resolutions[0] ?? null,
      });
    } else {
      setPending({ ticket: current.ticket, column: target, options, place });
    }
  };

  const columnState = (index: number): 'idle' | 'allowed' | 'blocked' => {
    if (!drag || !data || index === drag.from || !drag.options) return 'idle';
    const options = optionsFor(data.board, index, drag.options, drag.ticket.type);
    return options.some((o) => o.available) ? 'allowed' : 'blocked';
  };

  return {
    drag: drag?.ticket ?? null,
    pending,
    columnState,
    onDragStart,
    onDragEnd,
    cancel: () => setDrag(null),
    closePending: () => {
      restore();
      setPending(null);
    },
    resolve: (body: Omit<CardMove, 'ticket' | 'column'>) => {
      before.current = undefined;
      if (pending)
        move.mutate({
          ticket: pending.ticket.key,
          column: pending.column,
          ...pending.place,
          ...body,
        });
      setPending(null);
    },
  };
}
