import type { Tone } from './style';

/** Status colors and panel kinds mapped onto the theme's tones. */
export function toneOf(name: string): Tone {
  if (name === 'green' || name === 'info' || name === 'tip' || name === 'note') return 'accent';
  if (name === 'yellow' || name === 'warning') return 'warning';
  if (name === 'red' || name === 'error') return 'danger';
  return 'muted';
}
