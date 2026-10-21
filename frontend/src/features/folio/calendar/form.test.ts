import { describe, expect, it } from 'vitest';
import { AGENDA } from './fixtures';
import { blankForm, bodyOf, formOf, toggleAllDay } from './form';

describe('event form', () => {
  it('sends all-day events with an exclusive end', () => {
    const form = { ...blankForm(new Date(2026, 11, 14)), title: ' Viaje ', allDay: true };
    const body = bodyOf({ ...form, start: '2026-12-14', end: '2026-12-15', people: '@ana, luis' });
    expect(body).toMatchObject({
      title: 'Viaje',
      all_day: true,
      start_at: '2026-12-14T00:00:00Z',
      end_at: '2026-12-16T00:00:00Z',
      people: ['ana', 'luis'],
    });
  });

  it('round-trips an event into the form', () => {
    const vacation = formOf(AGENDA.events[1]!);
    expect(vacation).toMatchObject({ allDay: true, start: '2026-12-14', end: '2026-12-15' });
    const release = formOf(AGENDA.events[0]!);
    expect(release.start).toBe('2026-12-10T15:00');
    expect(bodyOf(release).start_at).toBe(AGENDA.events[0]!.start_at);
  });

  it('toggles all-day keeping the days', () => {
    const timed = blankForm(new Date(2026, 11, 3));
    const allDay = toggleAllDay(timed, true);
    expect(allDay).toMatchObject({ start: '2026-12-03', end: '2026-12-03' });
    expect(toggleAllDay(allDay, false).start).toBe('2026-12-03T10:00');
    expect(toggleAllDay(allDay, true)).toBe(allDay);
  });
});
