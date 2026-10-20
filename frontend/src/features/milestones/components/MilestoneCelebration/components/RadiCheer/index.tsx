import { useEffect, useRef } from 'react';
import { Engine, RIG } from '../../../../../assistant/lib/engine';
import { renderRadi } from '../../../../../assistant/lib/render';
import * as S from './style';

const CHEER_EVERY = 2.6; // seconds

/** Radi, happy, waving and bouncing now and then. */
export function RadiCheer() {
  const art = useRef<HTMLSpanElement>(null);
  const engine = useRef(new Engine(RIG));

  useEffect(() => {
    const radi = engine.current;
    radi.wake();
    radi.setExpression('happy');
    radi.play('wave');
    const draw = (dt: number) => {
      if (art.current) art.current.innerHTML = renderRadi(radi.rig, radi.step(dt), 'radi-cheer');
    };
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      draw(0.5);
      return;
    }
    // Cheers follow the animation clock, not a timer: a timer keeps firing while the tab is
    // hidden and frames are paused, and the piled-up jumps all play at once on return.
    let since = 0;
    let frame = 0;
    let last = 0;
    const loop = (now: number) => {
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now;
      since += dt;
      if (since > CHEER_EVERY) {
        since = 0;
        radi.play(Math.random() < 0.5 ? 'surprise' : 'wave');
      }
      draw(dt);
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <S.Art
      ref={art}
      onPointerEnter={() => engine.current.setHover(true)}
      onPointerLeave={() => engine.current.setHover(false)}
    />
  );
}
