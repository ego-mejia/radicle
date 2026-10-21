import { describe, expect, it } from 'vitest';
import { byDay, dayKey, eventDays, shift, startOfWeek, viewDays, viewRange } from './dates';

describe('calendar dates', () => {
  it('starts weeks on Monday and shows six weeks for a month', () => {
    expect(dayKey(startOfWeek(new Date(2026, 11, 3)))).toBe('2026-11-30');
    expect(dayKey(startOfWeek(new Date(2026, 10, 30)))).toBe('2026-11-30');
    const month = viewDays(new Date(2026, 11, 15), 'month');
    expect(month).toHaveLength(42);
    expect(dayKey(month[0]!)).toBe('2026-11-30');
    const week = viewDays(new Date(2026, 11, 15), 'week');
    expect(week.map(dayKey)).toEqual([
      '2026-12-14',
      '2026-12-15',
      '2026-12-16',
      '2026-12-17',
      '2026-12-18',
      '2026-12-19',
      '2026-12-20',
    ]);
    const range = viewRange(week);
    expect(new Date(range.end).getTime() - new Date(range.start).getTime()).toBeGreaterThan(0);
  });

  it('moves by month or week', () => {
    expect(dayKey(shift(new Date(2026, 11, 15), 'month', 1))).toBe('2027-01-01');
    expect(dayKey(shift(new Date(2026, 11, 15), 'week', -1))).toBe('2026-12-08');
  });

  it('places all-day events on their UTC days, end exclusive', () => {
    const trip = {
      start_at: '2026-12-14T00:00:00Z',
      end_at: '2026-12-16T00:00:00Z',
      all_day: true,
    };
    expect(eventDays(trip)).toEqual(['2026-12-14', '2026-12-15']);
  });

  it('places timed events on local days and sorts them', () => {
    const a = new Date(2026, 11, 3, 10).toISOString();
    const b = new Date(2026, 11, 3, 9).toISOString();
    const late = { start_at: a, end_at: new Date(2026, 11, 3, 11).toISOString(), all_day: false };
    const early = { start_at: b, end_at: new Date(2026, 11, 3, 10).toISOString(), all_day: false };
    expect(eventDays(late)).toEqual(['2026-12-03']);
    expect(byDay([late, early]).get('2026-12-03')).toEqual([early, late]);
    const night = {
      start_at: new Date(2026, 11, 3, 22).toISOString(),
      end_at: new Date(2026, 11, 4, 2).toISOString(),
      all_day: false,
    };
    expect(eventDays(night)).toEqual(['2026-12-03', '2026-12-04']);
  });
});
