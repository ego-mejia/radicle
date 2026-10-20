/**
 * Radicle logo: Radi, the mascot, as a green tile with his two eyes.
 */
import { Svg } from './style';

type Props = { size?: number; title?: string };

export function Logo({ size = 32, title = 'Radicle' }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label={title}>
      <rect className="badge" width="32" height="32" rx="8" />
      <ellipse className="eye" cx="11.4" cy="15.5" rx="2.6" ry="4.1" />
      <ellipse className="eye" cx="20.6" cy="15.5" rx="2.6" ry="4.1" />
    </Svg>
  );
}
