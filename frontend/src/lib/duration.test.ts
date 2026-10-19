import { describe, expect, it } from 'vitest';
import { formatHours, formatMinutes, parseDuration } from './duration';

describe('durations', () => {
  it('reads what people type', () => {
    expect(parseDuration('90')).toBe(90);
    expect(parseDuration('1h 30m')).toBe(90);
    expect(parseDuration('1.5h')).toBe(90);
    expect(parseDuration('2h')).toBe(120);
    expect(parseDuration('45m')).toBe(45);
    expect(parseDuration('1,25h')).toBe(75);
    expect(parseDuration('mucho')).toBeNull();
    expect(parseDuration('')).toBeNull();
  });

  it('formats', () => {
    expect(formatMinutes(150)).toBe('2h 30m');
    expect(formatMinutes(45)).toBe('45m');
    expect(formatHours(2)).toBe('2h');
    expect(formatHours(null)).toBe('—');
  });
});
