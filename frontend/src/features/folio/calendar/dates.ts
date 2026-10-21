// Dates for the calendar views (Folio 5.8). Weeks start on Monday. Timed events show on
// the reader's local days; all-day events are whole UTC days with an exclusive end.

import type { CalendarEvent } from '../../../services/api/folioCalendars';

export type CalendarMode = 'month' | 'week';

const DAY = 86_400_000;

/** A local day as yyyy-mm-dd. */
export function dayKey(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
}

export function addDays(d: Date, days: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + days);
}

export function startOfWeek(d: Date): Date {
  const shift = (d.getDay() + 6) % 7; // Monday is 0
  return addDays(d, -shift);
}

/** The days a view shows: six weeks around the month, or one week. */
export function viewDays(anchor: Date, mode: CalendarMode): Date[] {
  const first =
    mode === 'month'
      ? startOfWeek(new Date(anchor.getFullYear(), anchor.getMonth(), 1))
      : startOfWeek(anchor);
  const count = mode === 'month' ? 42 : 7;
  return Array.from({ length: count }, (_, i) => addDays(first, i));
}

/** The next or previous month or week. */
export function shift(anchor: Date, mode: CalendarMode, step: 1 | -1): Date {
  return mode === 'month'
    ? new Date(anchor.getFullYear(), anchor.getMonth() + step, 1)
    : addDays(anchor, 7 * step);
}

/** The range to ask the API for, as ISO instants (end exclusive). */
export function viewRange(days: Date[]): { start: string; end: string } {
  const first = days[0] ?? new Date();
  const last = days[days.length - 1] ?? first;
  return { start: first.toISOString(), end: addDays(last, 1).toISOString() };
}

/** The keys of the days an event covers. */
export function eventDays(event: Pick<CalendarEvent, 'start_at' | 'end_at' | 'all_day'>): string[] {
  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  const keys: string[] = [];
  if (event.all_day) {
    for (let t = start.getTime(); t < end.getTime(); t += DAY) {
      keys.push(new Date(t).toISOString().slice(0, 10));
    }
    return keys.length ? keys : [start.toISOString().slice(0, 10)];
  }
  const lastMoment = new Date(Math.max(start.getTime(), end.getTime() - 1));
  for (let d = start; dayKey(d) <= dayKey(lastMoment); d = addDays(d, 1)) {
    keys.push(dayKey(d));
    if (keys.length > 400) break;
  }
  return keys;
}

/** Events by the local day they show on, in start order. */
export function byDay<E extends Pick<CalendarEvent, 'start_at' | 'end_at' | 'all_day'>>(
  events: E[],
): Map<string, E[]> {
  const out = new Map<string, E[]>();
  const sorted = [...events].sort((a, b) => a.start_at.localeCompare(b.start_at));
  for (const event of sorted) {
    for (const key of eventDays(event)) out.set(key, [...(out.get(key) ?? []), event]);
  }
  return out;
}
