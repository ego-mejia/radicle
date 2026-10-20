import type { CardStat } from './celebrate';
import { Engine, RIG } from '../../assistant/lib/engine';
import { renderRadi } from '../../assistant/lib/render';
import { darkTheme } from '../../../styles/theme';

export type CardText = {
  badge: string; // "Milestone complete"
  title: string; // the milestone
  subtitle: string; // the project
  stats: CardStat[]; // up to six
  footer: string; // who did it
  brand: string; // "Tracked with Radicle"
};

// LinkedIn's recommended size for a shared image.
export const CARD_WIDTH = 1200;
export const CARD_HEIGHT = 627;
const C = darkTheme.color;
const FONT = darkTheme.fonts.ui;

function happyRadi(): Promise<HTMLImageElement> {
  const radi = new Engine(RIG);
  radi.setExpression('happy');
  let frame = radi.step(0);
  for (let i = 0; i < 40; i++) frame = radi.step(0.05); // let the smile settle
  const svg = renderRadi(RIG, frame, 'radi-card');
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  });
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 18);
  ctx.fill();
}

function fit(ctx: CanvasRenderingContext2D, text: string, max: number, size: number, weight = 800) {
  let px = size;
  ctx.font = `${weight} ${px}px ${FONT}`;
  while (ctx.measureText(text).width > max && px > 20) {
    px -= 2;
    ctx.font = `${weight} ${px}px ${FONT}`;
  }
}

/** The milestone's celebration as a PNG, ready to post. */
export async function drawShareCard(text: CardText): Promise<Blob> {
  const canvas = document.createElement('canvas');
  canvas.width = CARD_WIDTH;
  canvas.height = CARD_HEIGHT;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas is not available');

  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT);
  const glow = ctx.createRadialGradient(230, 330, 20, 230, 330, 360);
  glow.addColorStop(0, C.accentSoft);
  glow.addColorStop(1, C.bg);
  ctx.globalAlpha = 0.18;
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT);
  ctx.globalAlpha = 1;
  ctx.drawImage(await happyRadi(), 40, 120, 380, 380);

  const left = 460;
  const width = CARD_WIDTH - left - 60;
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = C.accentFill;
  ctx.font = `700 22px ${FONT}`;
  ctx.fillText(text.badge.toUpperCase(), left, 92);
  ctx.fillStyle = C.text;
  fit(ctx, text.title, width, 64);
  ctx.fillText(text.title, left, 160);
  ctx.fillStyle = C.textMuted;
  ctx.font = `500 26px ${FONT}`;
  ctx.fillText(text.subtitle, left, 202);

  const gap = 18;
  const boxW = (width - gap * 2) / 3;
  const boxH = 128;
  text.stats.slice(0, 6).forEach((stat, i) => {
    const x = left + (i % 3) * (boxW + gap);
    const y = 240 + Math.floor(i / 3) * (boxH + gap);
    ctx.fillStyle = C.surface2;
    roundRect(ctx, x, y, boxW, boxH);
    ctx.fillStyle = i === 0 ? C.accentFill : C.text;
    fit(ctx, stat.value, boxW - 40, 50);
    ctx.fillText(stat.value, x + 22, y + 66);
    ctx.fillStyle = C.textMuted;
    ctx.font = `500 20px ${FONT}`;
    ctx.fillText(stat.label, x + 22, y + 104);
  });

  ctx.fillStyle = C.text;
  ctx.font = `600 22px ${FONT}`;
  ctx.fillText(text.footer, left, 580);
  ctx.fillStyle = C.accentFill;
  ctx.font = `700 20px ${FONT}`;
  ctx.textAlign = 'right';
  ctx.fillText(text.brand, CARD_WIDTH - 60, 580);

  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('No image'))), 'image/png'),
  );
}
