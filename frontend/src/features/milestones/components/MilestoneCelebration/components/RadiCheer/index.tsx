import { useEffect, useRef } from 'react';
import { Engine, RIG } from '../../../../../assistant/lib/engine';
import { renderRadi } from '../../../../../assistant/lib/render';
import * as S from './style';

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
    const cheer = setInterval(() => radi.play(Math.random() < 0.5 ? 'surprise' : 'wave'), 2600);
    let frame = 0;
    let last = 0;
    const loop = (now: number) => {
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now;
      draw(dt);
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => {
      clearInterval(cheer);
      cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <S.Art
      ref={art}
      onPointerEnter={() => engine.current.setHover(true)}
      onPointerLeave={() => engine.current.setHover(false)}
    />
  );
}
