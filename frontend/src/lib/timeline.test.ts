import { describe, expect, it } from 'vitest';
import {
  arrowPath,
  barDates,
  dayRange,
  dragDates,
  flatten,
  spanOf,
  ticks,
  toDay,
  toIso,
  visibleRange,
  weekStart,
} from './timeline';

describe('timeline', () => {
  it('converts dates to days and back', () => {
    expect(toIso(toDay('2026-11-02'))).toBe('2026-11-02');
    expect(toDay('2026-11-03') - toDay('2026-11-02')).toBe(1);
    expect(toIso(weekStart(toDay('2026-11-05')))).toBe('2026-11-02');
  });

  it('pads the range and starts on a Monday', () => {
    const [first, last] = dayRange(['2026-11-10', null, '2026-12-01'], '2026-11-05');
    expect(toIso(first)).toBe('2026-10-26');
    expect(toIso(last)).toBe('2026-12-15');
  });

  it('builds spans and points', () => {
    expect(spanOf('2026-11-02', '2026-11-06')).toMatchObject({ point: false });
    expect(spanOf(null, '2026-11-06')).toMatchObject({ point: true });
    expect(spanOf(null, null)).toBeNull();
  });

  it('fills in the missing end of a bar', () => {
    const base = { created_at: '2026-10-20T15:00:00Z', estimate_hours: 20 };
    expect(barDates({ ...base, start_date: '2026-11-02', due_date: '2026-11-06' })).toEqual({
      start: '2026-11-02',
      due: '2026-11-06',
      inferred: null,
    });
    // Only a due date: from the day it was created.
    expect(barDates({ ...base, start_date: null, due_date: '2026-11-06' })).toEqual({
      start: '2026-10-20',
      due: '2026-11-06',
      inferred: 'start',
    });
    // Created after its due date: a one-day bar.
    expect(barDates({ ...base, start_date: null, due_date: '2026-10-01' })?.start).toBe(
      '2026-10-01',
    );
    // Only a start: 20 h at 8 h a day is 3 days.
    expect(barDates({ ...base, start_date: '2026-11-02', due_date: null })).toEqual({
      start: '2026-11-02',
      due: '2026-11-04',
      inferred: 'due',
    });
    expect(barDates({ start_date: '2026-11-02', due_date: null })?.due).toBe('2026-11-02');
    expect(barDates({ start_date: null, due_date: null })).toBeNull();
  });

  it('drags the bar or one edge without crossing', () => {
    expect(dragDates('2026-11-02', '2026-11-06', 'move', 7)).toEqual({
      start_date: '2026-11-09',
      due_date: '2026-11-13',
    });
    expect(dragDates('2026-11-02', '2026-11-06', 'start', 10)).toEqual({
      start_date: '2026-11-06',
      due_date: '2026-11-06',
    });
    expect(dragDates('2026-11-02', '2026-11-06', 'end', 2).due_date).toBe('2026-11-08');
    expect(dragDates(null, '2026-11-06', 'move', -1).due_date).toBe('2026-11-05');
  });

  it('labels ticks per zoom', () => {
    const first = toDay('2026-11-01');
    const last = toDay('2026-12-31');
    expect(ticks(first, last, 'quarter', 'en').map((t) => t.label)).toEqual([
      'Nov 2026',
      'Dec 2026',
    ]);
    expect(ticks(first, first + 13, 'month', 'en')[0]!.label).toBe('2 Nov');
  });

  it('flattens groups and skips collapsed ones', () => {
    const groups = [
      { key: 'a', label: 'V1', tickets: [{ key: 'PA-1' }, { key: 'PA-2' }] },
      { key: 'b', label: 'V2', tickets: [{ key: 'PA-3' }] },
    ];
    expect(flatten(groups, new Set(['a'])).map((r) => r.key)).toEqual(['a', 'b', 'PA-3']);
  });

  it('virtualizes rows', () => {
    expect(visibleRange(3000, 600, 30, 1000, 0)).toEqual([100, 120]);
  });

  it('draws arrows forward and around', () => {
    expect(arrowPath(0, 10, 50, 40)).toBe('M0,10 H8 V40 H50');
    expect(arrowPath(50, 10, 20, 40)).toContain('V25');
  });
});
