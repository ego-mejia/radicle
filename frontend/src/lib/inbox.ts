import type { Classification } from '../services/api/types';

type Token = 'warning' | 'catProgress' | 'accent' | 'textMuted';

/** Theme color for each classification (dots in the table and the matrix). */
export function classificationToken(kind: Classification): Token {
  if (kind === 'complaint') return 'warning';
  if (kind === 'experiment') return 'catProgress';
  if (kind === 'idea') return 'accent';
  return 'textMuted';
}

export type Quadrant = 'quick_wins' | 'big_bets' | 'fillers' | 'not_worth';

/** Impact and effort go 1 to 5; 3 and up is "high". */
export function quadrant(impact: number, effort: number): Quadrant {
  const high = impact >= 3;
  const hard = effort >= 3;
  if (high && !hard) return 'quick_wins';
  if (high && hard) return 'big_bets';
  if (!high && !hard) return 'fillers';
  return 'not_worth';
}

/** Dot size in pixels for a number of votes. */
export function dotSize(votes: number): number {
  return Math.min(36, 14 + votes * 4);
}

export function score(impact: number | null, effort: number | null): number | null {
  return impact == null || effort == null ? null : impact * 2 - effort;
}
