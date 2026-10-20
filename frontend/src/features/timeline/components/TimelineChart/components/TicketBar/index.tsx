import { useRef, useState } from 'react';
import { useTheme } from 'styled-components';
import {
  barDates,
  categoryToken,
  dragDates,
  type DragMode,
  spanOf,
} from '../../../../../../lib/timeline';
import type { TimelineTicket } from '../../../../../../services/api/types';

type Props = {
  ticket: TimelineTicket;
  y: number;
  height: number;
  origin: number;
  px: number;
  canEdit: boolean;
  onOpen: () => void;
  onCommit: (dates: { start_date: string | null; due_date: string | null }) => void;
};

type Drag = { mode: DragMode; x: number; delta: number };

/**
 * A ticket's bar: drag it to move both dates, or an edge to change one. With a single
 * date, the other end is filled in (see `barDates`) and the bar is drawn faded until
 * the ticket gets both dates.
 */
export function TicketBar({ ticket, y, height, origin, px, canEdit, onOpen, onCommit }: Props) {
  const theme = useTheme();
  const [drag, setDrag] = useState<Drag | null>(null);
  const moved = useRef(false);
  const bar = barDates(ticket);
  if (!bar) return null;
  const dates = drag
    ? dragDates(bar.start, bar.due, drag.mode, drag.delta)
    : { start_date: bar.start, due_date: bar.due };
  const span = spanOf(dates.start_date, dates.due_date)!;
  const faded = bar.inferred !== null && !drag;
  const color = theme.color[categoryToken(ticket.status.category)];
  const x = (span.start - origin) * px;
  const width = (span.end - span.start + 1) * px;
  const mid = y + height / 2;

  const begin = (mode: DragMode) => (e: React.PointerEvent<SVGElement>) => {
    if (!canEdit || e.button !== 0) return;
    e.stopPropagation();
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    moved.current = false;
    setDrag({ mode, x: e.clientX, delta: 0 });
  };
  const onMove = (e: React.PointerEvent<SVGElement>) => {
    if (!drag) return;
    const delta = Math.round((e.clientX - drag.x) / px);
    if (delta !== drag.delta) {
      moved.current = true;
      setDrag({ ...drag, delta });
    }
  };
  const onUp = () => {
    if (!drag) return;
    const changed = drag.delta !== 0;
    setDrag(null);
    if (changed) onCommit(dates);
  };
  const handlers = {
    onPointerMove: onMove,
    onPointerUp: onUp,
    onPointerCancel: () => setDrag(null),
  };
  const label = `${ticket.key} ${ticket.title}`;
  const shown = (date: string | null, which: 'start' | 'due') =>
    bar.inferred === which && !drag ? '—' : (date ?? '—');
  const tip = `${label} · ${shown(dates.start_date, 'start')} → ${shown(dates.due_date, 'due')}`;

  const textFits = width > 60;
  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={tip}
      data-testid={`bar-${ticket.key}`}
      onKeyDown={(e) => e.key === 'Enter' && onOpen()}
    >
      <title>{tip}</title>
      <rect
        x={x}
        y={y + 5}
        width={width}
        height={height - 10}
        rx={4}
        fill={color}
        opacity={drag ? 0.8 : faded ? 0.45 : 1}
        stroke={faded ? color : undefined}
        strokeDasharray={faded ? '4 3' : undefined}
        data-inferred={bar.inferred ?? undefined}
        style={{ cursor: canEdit ? 'grab' : 'pointer' }}
        onPointerDown={begin('move')}
        {...handlers}
        onClick={() => !moved.current && onOpen()}
      />
      {textFits && (
        <text
          x={x + 6}
          y={mid + 4}
          fontSize={11}
          fill={ticket.status.category === 'done' ? theme.color.surface : theme.color.onAccent}
          pointerEvents="none"
        >
          {ticket.key}
        </text>
      )}
      {!textFits && (
        <text
          x={x + width + 6}
          y={mid + 4}
          fontSize={11}
          fill={theme.color.text}
          pointerEvents="none"
        >
          {ticket.key}
        </text>
      )}
      {canEdit && (
        <>
          <rect
            x={x - 3}
            y={y + 5}
            width={7}
            height={height - 10}
            fill="transparent"
            style={{ cursor: 'ew-resize' }}
            data-testid={`edge-start-${ticket.key}`}
            onPointerDown={begin('start')}
            {...handlers}
          />
          <rect
            x={x + width - 4}
            y={y + 5}
            width={7}
            height={height - 10}
            fill="transparent"
            style={{ cursor: 'ew-resize' }}
            data-testid={`edge-end-${ticket.key}`}
            onPointerDown={begin('end')}
            {...handlers}
          />
        </>
      )}
    </g>
  );
}
