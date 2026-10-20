import { clamp, type Frame, type Rig } from './engine';

const f2 = (n: number) => Math.round(n * 100) / 100;

/**
 * Radi as an SVG string for one frame. The body sits on the ground and squashes from its
 * base; the eyes are ovals that look at the pointer. Happy eyes are the same ovals masked
 * from below (half moons); thinking lowers one "brow" with an angled cut on top.
 */
export function renderRadi(R: Rig, F: Frame, id = 'radi'): string {
  const cx = 128;
  const s = 1 + (R.hoverScale - 1) * F.hover;
  const r = R.size * s;
  const sy = 1 - F.squash;
  const sx = 1 + F.squash * 0.7 + Math.abs(F.stretchX);
  const bx = F.bodyX * R.bodyTravel;
  const by = F.bodyY * R.bodyTravel * 0.6;
  const tilt = F.tilt + F.bodyX * R.lean;
  const base = 128 + R.size;
  const cy = base - r;
  const out: string[] = [];
  out.push(
    `<g transform="translate(${f2(bx)} ${f2(F.lift + by)}) rotate(${f2(tilt)} ${cx} ${base}) translate(${cx} ${base}) scale(${f2(sx)} ${f2(sy)}) translate(${-cx} ${-base})">`,
    `<defs><clipPath id="${id}-body"><circle cx="${cx}" cy="${f2(cy)}" r="${f2(r)}"/></clipPath></defs>`,
    `<circle cx="${cx}" cy="${f2(cy)}" r="${f2(r)}" fill="${R.shade}"/>`,
    `<g clip-path="url(#${id}-body)"><circle cx="${f2(cx - r * 0.1)}" cy="${f2(cy - r * 0.12)}" r="${f2(r)}" fill="${R.body}"/>`,
    `<ellipse cx="${f2(cx - r * 0.56)}" cy="${f2(cy - r * 0.56)}" rx="${f2(r * 0.17)}" ry="${f2(r * 0.09)}" transform="rotate(-45 ${f2(cx - r * 0.56)} ${f2(cy - r * 0.56)})" fill="${R.light}" opacity="0.9"/>`,
    `<circle cx="${f2(cx - r * 0.34)}" cy="${f2(cy - r * 0.76)}" r="${f2(r * 0.045)}" fill="${R.light}" opacity="0.9"/></g>`,
  );
  const open = F.open * (1 + (R.hoverEyes - 1) * F.hover);
  const lid = clamp(Math.max(F.lid, F.blink), 0, 1);
  const ex = F.eyeX * R.eyeTravel * s;
  const ey = F.eyeY * R.eyeTravel * 0.75 * s;
  const happy = clamp(F.happy, 0, 1);
  for (const side of [-1, 1]) {
    const x = cx + ((side * R.eyeSep) / 2) * s * F.wide + ex - side * Math.abs(F.eyeX) * 2;
    const y = cy + R.eyeY * s + ey;
    // Turning narrows the eyes a little.
    const rx = R.eyeW * s * F.wide * (1 - Math.abs(F.eyeX) * 0.12);
    const brow = side < 0 ? F.browL : F.browR;
    const raised = Math.max(0, -brow);
    const ry0 = R.eyeH * s * open * (1 + raised * 0.2);
    const ry = Math.max(ry0 * (1 - lid), 1.6);
    // The lid closes from the top; a raised brow lifts the eye.
    const yc = y + (ry0 - ry) * 0.55 - raised * R.eyeH * s * 0.25;
    const mask = `${id}-eye${side}`;
    let cuts = '';
    if (happy > 0.01) {
      const mry = ry0 * 0.8;
      const my = yc + ry + mry - happy * ry * 1.15;
      cuts += `<ellipse cx="${f2(x)}" cy="${f2(my)}" rx="${f2(rx * 1.15)}" ry="${f2(mry)}" fill="#000"/>`;
    }
    if (brow > 0.01) {
      const edge = yc - ry + ry * 0.55 * brow;
      const angle = -side * 22 * brow;
      cuts += `<rect x="${f2(x - rx * 3)}" y="${f2(edge - 200)}" width="${f2(rx * 6)}" height="200" fill="#000" transform="rotate(${f2(angle)} ${f2(x)} ${f2(edge)})"/>`;
    }
    out.push(
      `<defs><mask id="${mask}" maskUnits="userSpaceOnUse" x="-200" y="-200" width="700" height="700"><rect x="-200" y="-200" width="700" height="700" fill="#fff"/>${cuts}</mask></defs>`,
      `<ellipse mask="url(#${mask})" cx="${f2(x)}" cy="${f2(yc)}" rx="${f2(rx)}" ry="${f2(ry)}" fill="${R.eyeColor}"/>`,
    );
  }
  if (F.sleepy > 0.5) {
    const tt = F.time % 2.4;
    for (let i = 0; i < 2; i++) {
      const p = (tt / 2.4 + i * 0.5) % 1;
      out.push(
        `<text x="${f2(cx + r * 0.75 + p * 24)}" y="${f2(cy - r * 0.7 - p * 40)}" font-family="Inter, sans-serif" font-weight="700" font-size="${f2(16 + p * 12)}" fill="${R.shade}" opacity="${f2(Math.sin(p * Math.PI))}">z</text>`,
      );
    }
  }
  out.push('</g>');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="30 30 196 196" aria-hidden="true">${out.join('')}</svg>`;
}
