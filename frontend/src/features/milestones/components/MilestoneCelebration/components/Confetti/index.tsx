import { useEffect, useRef } from 'react';
import { useTheme } from 'styled-components';
import { RIG } from '../../../../../assistant/lib/engine';
import * as S from './style';

type Piece = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  spin: number;
  angle: number;
  w: number;
  h: number;
  color: string;
};

const PIECES = 220;
const GRAVITY = 900; // px/s²
const DURATION = 4.5; // seconds

/** A burst of confetti from both bottom corners, in Radicle's greens. */
export function Confetti() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const theme = useTheme();

  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext?.('2d');
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    if (!el || !ctx || reduce) return;
    const ratio = window.devicePixelRatio || 1;
    const width = window.innerWidth;
    const height = window.innerHeight;
    el.width = width * ratio;
    el.height = height * ratio;
    ctx.scale(ratio, ratio);
    const colors = [
      theme.color.accentFill,
      theme.color.catDone,
      RIG.body,
      RIG.light,
      theme.color.warning,
      theme.color.surface,
    ];
    const pieces: Piece[] = Array.from({ length: PIECES }, (_, i) => {
      const left = i % 2 === 0;
      // Up and toward the middle: an angle from vertical, mirrored for the right corner.
      const tilt = 0.15 + Math.random() * 0.5;
      const speed = 700 + Math.random() * 650;
      return {
        x: left ? 0 : width,
        y: height,
        vx: (left ? 1 : -1) * Math.sin(tilt) * speed,
        vy: -Math.cos(tilt) * speed,
        spin: (Math.random() - 0.5) * 12,
        angle: Math.random() * Math.PI,
        w: 6 + Math.random() * 6,
        h: 10 + Math.random() * 8,
        color: colors[i % colors.length]!,
      };
    });
    let frame = 0;
    let last = 0;
    let elapsed = 0;
    const loop = (now: number) => {
      const dt = last ? Math.min(0.033, (now - last) / 1000) : 0;
      last = now;
      elapsed += dt;
      ctx.clearRect(0, 0, width, height);
      ctx.globalAlpha = Math.max(0, Math.min(1, (DURATION - elapsed) / 1.2));
      for (const p of pieces) {
        p.vy += GRAVITY * dt;
        p.vx *= 0.99;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.angle += p.spin * dt;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.angle);
        // Flat pieces turning in the air: the width shrinks and grows.
        ctx.scale(Math.cos(p.angle * 2), 1);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      }
      if (elapsed < DURATION) frame = requestAnimationFrame(loop);
      else ctx.clearRect(0, 0, width, height);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [theme]);

  return <S.Canvas ref={canvas} aria-hidden="true" />;
}
