import { useRef, useState } from 'react';
import { useTheme } from 'styled-components';
import { categoryToken, dragDates, type DragMode, spanOf } from '../../../../../../lib/timeline';
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

/** A ticket's bar (or point): drag it to move both dates, or an edge to change one. */
export function TicketBar({ ticket, y, height, origin, px, canEdit, onOpen, onCommit }: Props) {
  const theme = useTheme();
  const [drag, setDrag] = useState<Drag | null>(null);
  const moved = useRef(false);
  const dates = drag
    ? dragDates(ticket.start_date, ticket.due_date, drag.mode, drag.delta)
    : { start_date: ticket.start_date, due_date: ticket.due_date };
  const span = spanOf(dates.start_date, dates.due_date);
  if (!span) return null;
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
  const tip = `${label} · ${dates.start_date ?? '—'} → ${dates.due_date ?? '—'}`;

  if (span.point) {
    return (
      <g
        role="button"
        tabIndex={0}
        aria-label={tip}
        data-testid={`bar-${ticket.key}`}
        style={{ cursor: canEdit ? 'grab' : 'pointer' }}
        onPointerDown={begin('move')}
        {...handlers}
        onClick={() => !moved.current && onOpen()}
        onKeyDown={(e) => e.key === 'Enter' && onOpen()}
      >
        <title>{tip}</title>
        <circle
          cx={x + px / 2}
          cy={mid}
          r={6}
          fill={color}
          stroke={theme.color.text}
          strokeWidth={1}
        />
        <text x={x + px / 2 + 10} y={mid + 4} fontSize={11} fill={theme.color.text}>
          {ticket.key}
        </text>
      </g>
    );
  }
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
        opacity={drag ? 0.8 : 1}
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
