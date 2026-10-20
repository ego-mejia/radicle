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
export type PendingDrop = { ticket: BoardCard; column: number; options: TransitionOption[] };

function columnOf(data: BoardData, key: string): number {
  return data.columns.find((c) => c.tickets.some((t) => t.key === key))?.index ?? -1;
}

/** Drag and drop on a board: rank inside a column, move across columns through the API. */
export function useBoardDrag(data: BoardData | undefined, project: string) {
  const queryClient = useQueryClient();
  const feedback = useMoveFeedback();
  const [drag, setDrag] = useState<Drag | null>(null);
  const [pending, setPending] = useState<PendingDrop | null>(null);
  // The transitions request of the current drag: a quick drop waits for it.
  const request = useRef<Promise<TransitionOption[]> | null>(null);
  const boardId = data?.board.id ?? '';

  const move = useMutation({
    mutationFn: (body: CardMove) => moveCard(boardId, body),
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
    const before = overTicket && overTicket.key !== current.ticket.key ? overTicket.key : null;
    if (target === current.from) {
      if (before) move.mutate({ ticket: current.ticket.key, column: target, before });
      return;
    }
    const loaded = current.options ?? (await request.current?.catch(() => null));
    if (!loaded) return;
    const options = optionsFor(data.board, target, loaded, current.ticket.type);
    if (options.length === 0) return;
    const only = options[0]!;
    const resolutions = only.allowed_resolutions ?? [];
    const simple = only.available && !only.requires_comment && !only.has_screen;
    if (options.length === 1 && simple && (only.category !== 'done' || resolutions.length <= 1)) {
      move.mutate({
        ticket: current.ticket.key,
        column: target,
        before,
        transition: only.name,
        resolution: resolutions[0] ?? null,
      });
    } else {
      setPending({ ticket: current.ticket, column: target, options });
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
    closePending: () => setPending(null),
    resolve: (body: Omit<CardMove, 'ticket' | 'column'>) => {
      if (pending) move.mutate({ ticket: pending.ticket.key, column: pending.column, ...body });
      setPending(null);
    },
  };
}
