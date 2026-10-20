import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Engine, RIG } from '../../lib/engine';
import { renderRadi } from '../../lib/render';
import * as S from './style';

/** What Radi is doing: it changes his expression and plays a little action. */
export type RadiMood = 'idle' | 'listening' | 'thinking' | 'answered';

type Props = { open: boolean; mood: RadiMood; onClick: () => void };

// Drawing units across the button: the SVG viewBox is 196 units wide.
const VIEW = 196;

/** The green helper at the bottom right. His eyes follow the pointer all over the page. */
export function Radi({ open, mood, onClick }: Props) {
  const { t } = useTranslation();
  const button = useRef<HTMLButtonElement>(null);
  const art = useRef<HTMLSpanElement>(null);
  const engine = useRef(new Engine(RIG));

  useEffect(() => {
    const radi = engine.current;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    const draw = (dt: number) => {
      if (art.current) art.current.innerHTML = renderRadi(radi.rig, radi.step(dt));
    };
    const onMove = (e: PointerEvent) => {
      const box = button.current?.getBoundingClientRect();
      if (!box) return;
      const units = VIEW / box.width;
      radi.look(
        (e.clientX - box.left - box.width / 2) * units,
        (e.clientY - box.top - box.height / 2) * units,
      );
      if (reduce) draw(0.2);
    };
    window.addEventListener('pointermove', onMove);
    // During a tour Radi watches the tour cursor.
    const onLook = (e: Event) => {
      const { x, y } = (e as CustomEvent<{ x: number; y: number }>).detail;
      onMove({ clientX: x, clientY: y } as PointerEvent);
    };
    window.addEventListener('radi:look', onLook);
    let frame = 0;
    let last = 0;
    const loop = (now: number) => {
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now;
      if (!document.hidden) draw(dt);
      frame = requestAnimationFrame(loop);
    };
    if (reduce) draw(0.5);
    else frame = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('radi:look', onLook);
    };
  }, []);

  useEffect(() => {
    const radi = engine.current;
    radi.wake();
    if (mood === 'thinking') {
      radi.setExpression('thinking');
      radi.play('think');
    } else if (mood === 'answered') {
      radi.setExpression('idle');
      radi.play('talk');
    } else if (mood === 'listening') radi.setExpression('curious');
    else radi.setExpression('idle');
  }, [mood]);

  useEffect(() => {
    const radi = engine.current;
    radi.wake();
    if (open) radi.play('wave');
  }, [open]);

  return (
    <S.Button
      ref={button}
      data-tour="radi"
      type="button"
      aria-label={open ? t('assistant.close') : t('assistant.open')}
      aria-expanded={open}
      title={t('assistant.open')}
      onPointerEnter={() => engine.current.setHover(true)}
      onPointerLeave={() => engine.current.setHover(false)}
      onClick={() => {
        engine.current.play('press');
        onClick();
      }}
    >
      <S.Art ref={art} />
    </S.Button>
  );
}
