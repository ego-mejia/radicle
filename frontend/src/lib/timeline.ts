import type { Category } from '../services/api/types';

export type Zoom = 'week' | 'month' | 'quarter';
export const ZOOMS: Zoom[] = ['week', 'month', 'quarter'];
/** Pixels per day at each zoom. */
export const PX_PER_DAY: Record<Zoom, number> = { week: 36, month: 12, quarter: 4 };

const DAY_MS = 86_400_000;
/** dataTransfer type for dragging an undated ticket onto the chart. */
export const DRAG_TYPE = 'application/x-radicle-ticket';

/** Days since 1970-01-01 for a YYYY-MM-DD date (calendar days, no time zone shifts). */
export function toDay(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number);
  return Math.floor(Date.UTC(y!, m! - 1, d!) / DAY_MS);
}

export function toIso(day: number): string {
  return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

/** Monday on or before `day`. */
export function weekStart(day: number): number {
  const weekday = (new Date(day * DAY_MS).getUTCDay() + 6) % 7;
  return day - weekday;
}

/** First and last day to draw: every date in the data plus today, padded by a week. */
export function dayRange(dates: (string | null | undefined)[], today: string): [number, number] {
  const days = [...dates.filter((d): d is string => Boolean(d)).map(toDay), toDay(today)];
  const first = weekStart(Math.min(...days) - 7);
  const last = Math.max(...days) + 14;
  return [first, last];
}

export type Span = { start: number; end: number; point: boolean };

/** Bar extent in days: start to due, or a point when only one date exists. */
export function spanOf(start: string | null, due: string | null): Span | null {
  if (start && due) {
    const a = toDay(start);
    const b = toDay(due);
    return { start: Math.min(a, b), end: Math.max(a, b), point: false };
  }
  const only = due ?? start;
  if (!only) return null;
  return { start: toDay(only), end: toDay(only), point: true };
}

export type BarDates = { start: string; due: string; inferred: 'start' | 'due' | null };
const HOURS_PER_DAY = 8;

/**
 * The dates a ticket's bar spans. A missing start is its creation day (or the due date,
 * if it was created later); a missing due is the start plus its estimate at 8 h a day,
 * at least one day. `inferred` says which end was filled in, so it can be drawn faded.
 */
export function barDates(ticket: {
  start_date: string | null;
  due_date: string | null;
  created_at?: string | null;
  estimate_hours?: number | null;
}): BarDates | null {
  const { start_date: start, due_date: due } = ticket;
  if (start && due) return { start, due, inferred: null };
  if (due) {
    const created = ticket.created_at?.slice(0, 10);
    const from = created && created < due ? created : due;
    return { start: from, due, inferred: 'start' };
  }
  if (start) {
    const days = Math.max(1, Math.ceil((ticket.estimate_hours ?? 0) / HOURS_PER_DAY));
    return { start, due: toIso(toDay(start) + days - 1), inferred: 'due' };
  }
  return null;
}

export type DragMode = 'move' | 'start' | 'end';

/** New dates after dragging the bar (`move`) or one of its edges by `delta` days. */
export function dragDates(
  start: string | null,
  due: string | null,
  mode: DragMode,
  delta: number,
): { start_date: string | null; due_date: string | null } {
  const shift = (d: string | null) => (d ? toIso(toDay(d) + delta) : null);
  if (mode === 'move') return { start_date: shift(start), due_date: shift(due) };
  if (mode === 'start' && start) {
    const next = toDay(start) + delta;
    const limit = due ? toDay(due) : next;
    return { start_date: toIso(Math.min(next, limit)), due_date: due };
  }
  if (mode === 'end' && due) {
    const next = toDay(due) + delta;
    const limit = start ? toDay(start) : next;
    return { start_date: start, due_date: toIso(Math.max(next, limit)) };
  }
  return { start_date: start, due_date: due };
}

export type Tick = { day: number; label: string; major: boolean };

/** Labels along the top: days (week zoom), Mondays (month) or 1st of month (quarter). */
export function ticks(first: number, last: number, zoom: Zoom, locale: string): Tick[] {
  const out: Tick[] = [];
  const month = new Intl.DateTimeFormat(locale, { month: 'short', timeZone: 'UTC' });
  for (let day = first; day <= last; day++) {
    const date = new Date(day * DAY_MS);
    const dom = date.getUTCDate();
    const monday = date.getUTCDay() === 1;
    if (zoom === 'week') {
      out.push({ day, label: String(dom), major: dom === 1 || monday });
    } else if (zoom === 'month' && monday) {
      out.push({ day, label: `${dom} ${month.format(date)}`, major: dom <= 7 });
    } else if (zoom === 'quarter' && dom === 1) {
      out.push({ day, label: `${month.format(date)} ${date.getUTCFullYear()}`, major: true });
    }
  }
  return out;
}

export type Row<T> =
  | { kind: 'group'; key: string; label: string; count: number; collapsed: boolean }
  | { kind: 'ticket'; key: string; group: string; ticket: T };

/** Group headers followed by their tickets, unless the group is collapsed. */
export function flatten<T extends { key: string }>(
  groups: { key: string; label: string; tickets: T[] }[],
  collapsed: Set<string>,
): Row<T>[] {
  const rows: Row<T>[] = [];
  for (const g of groups) {
    const closed = collapsed.has(g.key);
    rows.push({
      kind: 'group',
      key: g.key,
      label: g.label,
      count: g.tickets.length,
      collapsed: closed,
    });
    if (!closed) {
      for (const ticket of g.tickets)
        rows.push({ kind: 'ticket', key: ticket.key, group: g.key, ticket });
    }
  }
  return rows;
}

/** Rows to render for a scroll position, with a few extra above and below. */
export function visibleRange(
  scrollTop: number,
  height: number,
  rowHeight: number,
  total: number,
  overscan = 8,
): [number, number] {
  const first = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const last = Math.min(total, Math.ceil((scrollTop + height) / rowHeight) + overscan);
  return [first, last];
}

/** Elbow path from the end of one bar to the start of another. */
export function arrowPath(x1: number, y1: number, x2: number, y2: number): string {
  const out = x1 + 8;
  const back = x2 - 8;
  if (back >= out) return `M${x1},${y1} H${out} V${y2} H${x2}`;
  const mid = (y1 + y2) / 2;
  return `M${x1},${y1} H${out} V${mid} H${back} V${y2} H${x2}`;
}

export function categoryToken(category: Category): 'catTodo' | 'catProgress' | 'catDone' {
  return category === 'todo' ? 'catTodo' : category === 'in_progress' ? 'catProgress' : 'catDone';
}
