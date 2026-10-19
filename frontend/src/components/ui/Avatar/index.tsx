import { Bot, Sprout } from 'lucide-react';
import { Circle } from './style';

type Props = {
  handle: string;
  name?: string;
  kind?: 'human' | 'agent' | 'system';
  size?: number;
};

function hue(text: string): number {
  let hash = 0;
  for (const ch of text) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
  return hash;
}

/** Initials for people, a bot for agents and a sprout for Radicle itself (system). */
export function Avatar({ handle, name, kind = 'human', size = 22 }: Props) {
  const label = name ? `${name} (@${handle})` : `@${handle}`;
  const initials = (name || handle)
    .split(/[\s_-]+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2);
  return (
    <Circle
      $size={size}
      $hue={hue(handle)}
      $agent={kind !== 'human'}
      title={label}
      aria-label={label}
      role="img"
    >
      {kind === 'agent' ? (
        <Bot aria-hidden />
      ) : kind === 'system' ? (
        <Sprout aria-hidden />
      ) : (
        initials
      )}
    </Circle>
  );
}
