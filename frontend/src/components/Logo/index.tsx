/**
 * Radicle logo: lime badge with a seed and its first root (the radicle).
 */
import { Svg } from './style';

type Props = { size?: number; title?: string };

export function Logo({ size = 32, title = 'Radicle' }: Props) {
  return (
    <Svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label={title}>
      <rect className="badge" width="32" height="32" rx="8" />
      <path
        className="mark"
        d="M16 7c-4 0-6.5 2.6-6.5 5.8 0 2.6 2 4.2 4.6 4.6M16 7c4 0 6.5 2.6 6.5 5.8 0 2.6-2 4.2-4.6 4.6M16 17.4v4.2c0 2-1.6 2.6-1.6 4.4"
      />
    </Svg>
  );
}
