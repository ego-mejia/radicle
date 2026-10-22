import { clamp, type Frame, type Rig } from './engine';

const f2 = (n: number) => Math.round(n * 100) / 100;
type P2 = [number, number];
type P3 = [number, number, number];

/** Camera distance in drawing units: lower means stronger perspective. */
const FOCAL = 420;
/** How far the head turns toward the pointer at full gaze, in degrees. */
const TURN = 24;
const RAD = Math.PI / 180;

/**
 * Radi's head is a sphere. The eyes and the highlight are drawn on a flat face and then
 * wrapped onto the sphere, turned toward the pointer and projected with perspective, so an
 * eye on the far side narrows and curves (the technique of the Bible Strong avatar lab,
 * AGPL, https://github.com/smontlouis/bible-strong-avatar-lab).
 */
const onSphere = (r: number, x: number, y: number): P3 => {
  const lon = x / r;
  const lat = y / r;
  return [r * Math.cos(lat) * Math.sin(lon), r * Math.sin(lat), r * Math.cos(lat) * Math.cos(lon)];
};

/** Pitch around X, then yaw around Y. */
const turn = ([x, y, z]: P3, yaw: number, pitch: number): P3 => {
  const y1 = y * Math.cos(pitch) - z * Math.sin(pitch);
  const z1 = y * Math.sin(pitch) + z * Math.cos(pitch);
  return [x * Math.cos(yaw) + z1 * Math.sin(yaw), y1, -x * Math.sin(yaw) + z1 * Math.cos(yaw)];
};

const project = ([x, y, z]: P3): P2 => {
  const s = FOCAL / (FOCAL - z);
  return [x * s, y * s];
};

const ellipse = (w: number, h: number, n = 40): P2[] =>
  Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 2;
    return [(w / 2) * Math.cos(a), (h / 2) * Math.sin(a)];
  });

/**
 * The eye minus a lower ellipse (`rx2` by `ry2`, centred at `my`): the top arc of the eye and
 * the upper arc of the cut, in drawing order. Both are convex and centred on x = 0.
 */
function halfMoon(eye: P2[], rx: number, ry: number, rx2: number, ry2: number, my: number): P2[] {
  const inCut = ([x, y]: P2) => (x / rx2) ** 2 + ((y - my) / ry2) ** 2 < 1;
  const keep = eye.map((p) => !inCut(p));
  if (keep.every(Boolean)) return eye;
  if (!keep.some(Boolean)) return [];
  const n = eye.length;
  const start = eye.findIndex((_, i) => keep[i] && !keep[(i - 1 + n) % n]);
  const top: P2[] = [];
  for (let i = 0; i < n; i++) {
    const j = (start + i) % n;
    if (!keep[j]) break;
    top.push(eye[j]!);
  }
  // The eye ring runs clockwise on screen (y down), so the kept arc ends on the left and the
  // cut's upper arc runs back left to right: angles from PI to 2 PI.
  const arc: P2[] = [];
  for (let i = 0; i <= 24; i++) {
    const a = Math.PI + (i / 24) * Math.PI;
    const p: P2 = [rx2 * Math.cos(a), my + ry2 * Math.sin(a)];
    if ((p[0] / rx) ** 2 + (p[1] / ry) ** 2 < 1) arc.push(p);
  }
  const endsLeft = top[top.length - 1]![0] < top[0]![0];
  return endsLeft ? [...top, ...arc] : [...top, ...arc.reverse()];
}

/**
 * The part of the polygon below a line through (0, edge) tilted by `angle`: the lowered brow.
 * The new straight edge is subdivided so it still follows the sphere after projection.
 */
function clipBelow(poly: P2[], edge: number, angle: number): P2[] {
  const nx = -Math.sin(angle);
  const ny = Math.cos(angle);
  const side = ([x, y]: P2) => x * nx + (y - edge) * ny;
  const cut: P2[] = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i]!;
    const b = poly[(i + 1) % poly.length]!;
    const sa = side(a);
    const sb = side(b);
    if (sa >= 0) cut.push(a);
    if (sa >= 0 !== sb >= 0) {
      const t = sa / (sa - sb);
      cut.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
    }
  }
  const out: P2[] = [];
  for (let i = 0; i < cut.length; i++) {
    const a = cut[i]!;
    const b = cut[(i + 1) % cut.length]!;
    out.push(a);
    if (Math.abs(side(a)) < 1e-6 && Math.abs(side(b)) < 1e-6) {
      for (let k = 1; k < 8; k++)
        out.push([a[0] + ((b[0] - a[0]) * k) / 8, a[1] + ((b[1] - a[1]) * k) / 8]);
    }
  }
  return out;
}

type Wrapped = { d: string; visible: boolean };

/** A flat face polygon wrapped onto the sphere at (cx, cy) and projected to the page. */
function wrap(r: number, cx: number, cy: number, pts: P2[], yaw: number, pitch: number): Wrapped {
  let front = 0;
  const out = pts.map(([x, y]) => {
    const p = turn(onSphere(r, x, y), yaw, pitch);
    if (p[2] > 0) front++;
    const [px, py] = project(p);
    return `${f2(cx + px)} ${f2(cy + py)}`;
  });
  return { d: out.length ? `M${out.join('L')}Z` : '', visible: front > pts.length / 2 };
}

/**
 * Radi as an SVG string for one frame. The body sits on the ground and squashes from its
 * base; the head turns toward the pointer and the eyes ride on it. Happy eyes are half moons
 * and thinking lowers one brow: both cuts happen on the flat face, so each eye stays one path.
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
  // The pointer turns the head; an expression's own gaze mostly moves the eyes instead.
  const yaw = clamp(F.eyeX - F.lookX * 0.75, -1, 1) * TURN * RAD;
  const pitch = -clamp(F.eyeY - F.lookY * 0.8, -1, 1) * TURN * 0.45 * RAD;
  const out: string[] = [];
  out.push(
    `<g transform="translate(${f2(bx)} ${f2(F.lift + by)}) rotate(${f2(tilt)} ${cx} ${base}) translate(${cx} ${base}) scale(${f2(sx)} ${f2(sy)}) translate(${-cx} ${-base})">`,
    `<defs><clipPath id="${id}-body"><circle cx="${cx}" cy="${f2(cy)}" r="${f2(r)}"/></clipPath></defs>`,
    `<circle cx="${cx}" cy="${f2(cy)}" r="${f2(r)}" fill="${R.shade}"/>`,
    `<g clip-path="url(#${id}-body)"><circle cx="${f2(cx - r * 0.1)}" cy="${f2(cy - r * 0.12)}" r="${f2(r)}" fill="${R.body}"/>`,
  );
  // The lamp stays up-left; the specular highlight rides on the surface as the head turns.
  const tiltHl = ([x, y]: P2): P2 => {
    const a = -Math.PI / 4;
    return [
      x * Math.cos(a) - y * Math.sin(a) - r * 0.56,
      x * Math.sin(a) + y * Math.cos(a) - r * 0.56,
    ];
  };
  const hl = wrap(r, cx, cy, ellipse(r * 0.34, r * 0.18).map(tiltHl), yaw, pitch);
  const dot = wrap(
    r,
    cx,
    cy,
    ellipse(r * 0.09, r * 0.09, 16).map(([x, y]) => [x - r * 0.34, y - r * 0.76]),
    yaw,
    pitch,
  );
  if (hl.visible) out.push(`<path d="${hl.d}" fill="${R.light}" opacity="0.9"/>`);
  if (dot.visible) out.push(`<path d="${dot.d}" fill="${R.light}" opacity="0.9"/>`);
  const open = F.open * (1 + (R.hoverEyes - 1) * F.hover);
  const lid = clamp(Math.max(F.lid, F.blink), 0, 1);
  const happy = clamp(F.happy, 0, 1);
  // The eyes also slide a little over the surface, on top of the head turn.
  const ex = F.eyeX * R.eyeTravel * s * 0.4;
  const ey = F.eyeY * R.eyeTravel * s * 0.3;
  for (const side of [-1, 1]) {
    const brow = side < 0 ? F.browL : F.browR;
    const raised = Math.max(0, -brow);
    const w = 2 * R.eyeW * s * F.wide;
    const h0 = 2 * R.eyeH * s * open * (1 + raised * 0.2);
    const h = Math.max(h0 * (1 - lid), 3.2);
    const x0 = ((side * R.eyeSep) / 2) * s * F.wide + ex;
    // The lid closes from the top; a raised brow lifts the eye.
    const y0 = R.eyeY * s + ey + (h0 - h) * 0.55 - raised * R.eyeH * s * 0.25;
    let pts = ellipse(w, h);
    if (happy > 0.01) {
      const ry2 = h0 * 0.4;
      pts = halfMoon(pts, w / 2, h / 2, w * 0.575, ry2, h / 2 + ry2 - happy * h * 0.575);
    }
    if (brow > 0.01) pts = clipBelow(pts, -h / 2 + h * 0.55 * brow, -side * 22 * brow * RAD);
    const eye = wrap(
      r,
      cx,
      cy,
      pts.map(([x, y]) => [x0 + x, y0 + y]),
      yaw,
      pitch,
    );
    if (eye.visible) out.push(`<path d="${eye.d}" fill="${R.eyeColor}"/>`);
  }
  out.push('</g>');
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
