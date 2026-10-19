import { describe, expect, it } from 'vitest';
import { dotSize, quadrant, score } from './inbox';

describe('inbox', () => {
  it('names the quadrants', () => {
    expect(quadrant(5, 1)).toBe('quick_wins');
    expect(quadrant(4, 5)).toBe('big_bets');
    expect(quadrant(1, 2)).toBe('fillers');
    expect(quadrant(2, 4)).toBe('not_worth');
  });

  it('scores and sizes', () => {
    expect(score(5, 2)).toBe(8);
    expect(score(null, 2)).toBeNull();
    expect(dotSize(0)).toBe(14);
    expect(dotSize(100)).toBe(36);
  });
});
