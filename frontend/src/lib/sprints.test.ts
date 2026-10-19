import { describe, expect, it } from 'vitest';
import { isoPlus, sprintDays } from './sprints';

describe('sprints', () => {
  it('counts both ends', () => {
    expect(sprintDays('2026-10-19', '2026-10-19')).toBe(1);
    expect(sprintDays('2026-10-19', '2026-11-01')).toBe(14);
    expect(sprintDays('2026-10-19', '2026-10-18')).toBe(0);
  });

  it('adds days in local time', () => {
    expect(isoPlus(13, new Date(2026, 9, 19))).toBe('2026-11-01');
  });
});
