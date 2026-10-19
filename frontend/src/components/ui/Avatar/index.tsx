import { Bot } from 'lucide-react';
import { Circle } from './style';

type Props = {
  handle: string;
  name?: string;
  kind?: 'human' | 'agent';
  size?: number;
};

function hue(text: string): number {
  let hash = 0;
  for (const ch of text) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
  return hash;
}

/** Initials for people, a bot icon for agents. */
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
      $agent={kind === 'agent'}
      title={label}
      aria-label={label}
      role="img"
    >
      {kind === 'agent' ? <Bot aria-hidden /> : initials}
    </Circle>
  );
}
