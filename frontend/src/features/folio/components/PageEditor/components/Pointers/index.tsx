import { MousePointer2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type RefObject } from 'react';
import {
  POINTER_EVERY_MS,
  POINTER_IDLE_MS,
  throttle,
  type Peer,
  type Pointer,
} from '../../../../editor/presence';
import * as S from './style';

type Awareness = { setLocalStateField(field: string, value: unknown): void };

type Props = {
  /** The page the pointers move over; positions are relative to it. */
  container: RefObject<HTMLElement | null>;
  awareness: Awareness;
  peers: Peer[];
};

/** Everyone's mouse over the page, Figma-like, with their name; a still pointer fades after 10 s. */
export function Pointers({ container, awareness, peers }: Props) {
  const [now, setNow] = useState(() => Date.now());
  // When each pointer last moved, by this browser's clock: other clocks may be off.
  const moved = useRef(new Map<number, { at: number; seen: number }>());

  const send = useMemo(
    () =>
      throttle(
        (pointer: Pointer | null) => awareness.setLocalStateField('pointer', pointer),
        POINTER_EVERY_MS,
      ),
    [awareness],
  );
  useEffect(() => {
    const el = container.current;
    if (!el) return;
    const onMove = (event: MouseEvent) => {
      const box = el.getBoundingClientRect();
      send({
        x: Math.round(event.clientX - box.left),
        y: Math.round(event.clientY - box.top),
        at: Date.now(),
      });
    };
    const onLeave = () => send(null);
    el.addEventListener('mousemove', onMove);
    el.addEventListener('mouseleave', onLeave);
    return () => {
      el.removeEventListener('mousemove', onMove);
      el.removeEventListener('mouseleave', onLeave);
    };
  }, [container, send]);

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const shown = peers.filter((peer) => {
    if (!peer.pointer) return false;
    const last = moved.current.get(peer.clientId);
    if (!last || last.at !== peer.pointer.at) {
      moved.current.set(peer.clientId, { at: peer.pointer.at, seen: Date.now() });
      return true;
    }
    return now - last.seen < POINTER_IDLE_MS;
  });

  return (
    <S.Layer aria-hidden>
      {shown.map((peer) => (
        <S.Pointer
          key={peer.clientId}
          data-testid="pointer"
          style={{ transform: `translate(${peer.pointer?.x ?? 0}px, ${peer.pointer?.y ?? 0}px)` }}
        >
          <MousePointer2 size={18} fill={peer.color} color={peer.color} />
          <S.Name $color={peer.color}>{peer.name}</S.Name>
        </S.Pointer>
      ))}
    </S.Layer>
  );
}
