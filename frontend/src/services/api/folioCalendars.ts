// Folio calendars (5.8): a space's calendars, their events and the Docket milestones
// they show. The iCal feed is at each calendar's `ical_path`, outside /api.

import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type FolioCalendar = S['CalendarOut'];
export type CalendarEvent = S['CalendarEventOut'];
export type CalendarMilestone = S['CalendarMilestoneOut'];
export type CalendarAgenda = S['AgendaOut'];
export type CalendarInput = S['CalendarIn'];
export type CalendarPatch = S['CalendarPatch'];
export type CalendarEventInput = S['CalendarEventIn'];
export type CalendarEventPatch = S['CalendarEventPatch'];
export type CalendarColor = FolioCalendar['color'];
export type EventCategory = CalendarEvent['category'];

export const calendarKeys = {
  all: ['folio', 'calendars'] as const,
  list: (space: string) => ['folio', 'calendars', 'space', space] as const,
  calendar: (id: string) => ['folio', 'calendars', id] as const,
  agenda: (id: string, start: string, end: string) =>
    ['folio', 'calendars', id, 'agenda', start, end] as const,
};

export async function fetchCalendars(space: string): Promise<FolioCalendar[]> {
  const out = unwrap(await api.GET('/api/v1/folio/calendars', { params: { query: { space } } }));
  return out.items;
}

export async function fetchCalendar(id: string): Promise<FolioCalendar> {
  return unwrap(
    await api.GET('/api/v1/folio/calendars/{calendar_id}', {
      params: { path: { calendar_id: id } },
    }),
  );
}

export async function createCalendar(body: CalendarInput): Promise<FolioCalendar> {
  return unwrap(await api.POST('/api/v1/folio/calendars', { body }));
}

export async function updateCalendar(id: string, body: CalendarPatch): Promise<FolioCalendar> {
  return unwrap(
    await api.PATCH('/api/v1/folio/calendars/{calendar_id}', {
      params: { path: { calendar_id: id } },
      body,
    }),
  );
}

export async function rotateFeed(id: string): Promise<FolioCalendar> {
  return unwrap(
    await api.POST('/api/v1/folio/calendars/{calendar_id}/ical-token', {
      params: { path: { calendar_id: id } },
    }),
  );
}

export async function deleteCalendar(id: string): Promise<void> {
  unwrap(
    await api.DELETE('/api/v1/folio/calendars/{calendar_id}', {
      params: { path: { calendar_id: id } },
    }),
  );
}

export async function fetchAgenda(id: string, start: string, end: string): Promise<CalendarAgenda> {
  return unwrap(
    await api.GET('/api/v1/folio/calendars/{calendar_id}/events', {
      params: { path: { calendar_id: id }, query: { start, end } },
    }),
  );
}

export async function createEvent(id: string, body: CalendarEventInput): Promise<CalendarEvent> {
  return unwrap(
    await api.POST('/api/v1/folio/calendars/{calendar_id}/events', {
      params: { path: { calendar_id: id } },
      body,
    }),
  );
}

export async function updateEvent(
  id: string,
  eventId: string,
  body: CalendarEventPatch,
): Promise<CalendarEvent> {
  return unwrap(
    await api.PATCH('/api/v1/folio/calendars/{calendar_id}/events/{event_id}', {
      params: { path: { calendar_id: id, event_id: eventId } },
      body,
    }),
  );
}

export async function deleteEvent(id: string, eventId: string): Promise<void> {
  unwrap(
    await api.DELETE('/api/v1/folio/calendars/{calendar_id}/events/{event_id}', {
      params: { path: { calendar_id: id, event_id: eventId } },
    }),
  );
}

/** The feed's full URL, for Google Calendar or Outlook. */
export function feedUrl(calendar: FolioCalendar): string {
  return new URL(calendar.ical_path, window.location.origin).toString();
}
