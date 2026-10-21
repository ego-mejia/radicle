// The event form's values and how they map to the API (Folio 5.8). All-day events are
// typed with an inclusive last day; the API stores an exclusive end.

import type {
  CalendarEvent,
  CalendarEventInput,
  EventCategory,
} from '../../../services/api/folioCalendars';
import { dayKey } from './dates';

export type EventForm = {
  title: string;
  allDay: boolean;
  /** yyyy-mm-dd for all-day events, else yyyy-mm-ddThh:mm (local). */
  start: string;
  end: string;
  category: EventCategory;
  description: string;
  people: string;
};

function localMinute(d: Date): string {
  const h = String(d.getHours()).padStart(2, '0');
  const m = String(d.getMinutes()).padStart(2, '0');
  return `${dayKey(d)}T${h}:${m}`;
}

function utcDay(iso: string, days = 0): string {
  const d = new Date(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** A blank form for a day (default today), one hour from 10:00. */
export function blankForm(day = new Date()): EventForm {
  const start = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 10);
  const end = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 11);
  return {
    title: '',
    allDay: false,
    start: localMinute(start),
    end: localMinute(end),
    category: 'event',
    description: '',
    people: '',
  };
}

export function formOf(event: CalendarEvent): EventForm {
  return {
    title: event.title,
    allDay: event.all_day,
    start: event.all_day ? utcDay(event.start_at) : localMinute(new Date(event.start_at)),
    end: event.all_day ? utcDay(event.end_at, -1) : localMinute(new Date(event.end_at)),
    category: event.category,
    description: event.description,
    people: event.people.join(', '),
  };
}

/** Switching to all-day keeps the days; back to timed starts at 10:00. */
export function toggleAllDay(form: EventForm, allDay: boolean): EventForm {
  if (allDay === form.allDay) return form;
  if (allDay)
    return { ...form, allDay, start: form.start.slice(0, 10), end: form.end.slice(0, 10) };
  return { ...form, allDay, start: `${form.start}T10:00`, end: `${form.end}T11:00` };
}

export function bodyOf(form: EventForm): CalendarEventInput {
  const people = form.people
    .split(/[\s,]+/)
    .map((p) => p.replace(/^@/, ''))
    .filter(Boolean);
  const range = form.allDay
    ? {
        start_at: `${form.start}T00:00:00Z`,
        end_at: `${utcDay(`${form.end}T00:00:00Z`, 1)}T00:00:00Z`,
      }
    : {
        start_at: new Date(form.start).toISOString(),
        end_at: new Date(form.end).toISOString(),
      };
  return {
    title: form.title.trim(),
    all_day: form.allDay,
    category: form.category,
    description: form.description,
    people,
    ...range,
  };
}
