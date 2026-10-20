/**
 * Radi's animation engine, from the animation lab: a parametric rig, expressions, actions
 * keyed with Disney's principles (anticipation, squash and stretch, follow-through,
 * overlapping action, slow in and out) and springs that follow the pointer.
 */

export const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** Character art: Radi's own palette, like the logo, not UI theme colors. */
export const RIG = {
  size: 74,
  body: '#7BC62D',
  shade: '#4D8F12',
  light: '#B6EC5E',
  eyeColor: '#FFFFFF',
  eyeW: 13,
  eyeH: 21,
  eyeSep: 50,
  eyeY: -10,
  eyeTravel: 15,
  bodyTravel: 6,
  lean: 6,
  hoverScale: 1.12,
  hoverEyes: 1.3,
  squashAmt: 1,
  bounce: 0.55,
};
export type Rig = typeof RIG;

const EXPR0 = {
  open: 1,
  wide: 1,
  lid: 0,
  happy: 0,
  lookX: 0,
  lookY: 0,
  tilt: 0,
  squash: 0,
  sleepy: 0,
  browL: 0,
  browR: 0,
};
type Expr = typeof EXPR0;
export type Expression = 'idle' | 'curious' | 'happy' | 'thinking' | 'surprised' | 'asleep';
const EXPRESSIONS: Record<Expression, Partial<Expr>> = {
  idle: {},
  curious: { open: 1.18, wide: 1.06, tilt: -4 },
  happy: { happy: 1, squash: 0.03 },
  thinking: { browL: 0.85, browR: -0.8, lookX: 0.85, lookY: -0.9, tilt: 5 },
  surprised: { open: 1.38, wide: 1.12, squash: -0.05 },
  asleep: { lid: 1, sleepy: 1, squash: 0.05, tilt: -3 },
};

export type Frame = Expr & {
  time: number;
  lift: number;
  blink: number;
  eyeX: number;
  eyeY: number;
  bodyX: number;
  bodyY: number;
  hover: number;
  stretchX: number;
};

type Ease = 'io' | 'out' | 'in' | 'back';
const EASE: Record<Ease, (p: number) => number> = {
  io: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
  out: (p) => 1 - Math.pow(1 - p, 3),
  in: (p) => p * p * p,
  back: (p) => {
    const c = 1.70158;
    return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2);
  },
};
type Key = [number, number, Ease?];
export function kf(t: number, keys: Key[]): number {
  if (t <= keys[0]![0]) return keys[0]![1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1, e] = keys[i]!;
    const [t0, v0] = keys[i - 1]!;
    if (t <= t1) return lerp(v0, v1, EASE[e ?? 'io']((t - t0) / (t1 - t0)));
  }
  return keys[keys.length - 1]![1];
}
function blinkCurve(t: number): number {
  if (t < 0.06) return EASE.in(t / 0.06);
  if (t < 0.1) return 1;
  if (t < 0.25) return 1 - EASE.out((t - 0.1) / 0.15);
  return 0;
}

export type Action = 'wave' | 'press' | 'surprise' | 'think' | 'talk' | 'nudge' | 'blink';
const ACTIONS: Record<Action, { dur: number; apply: (t: number, F: Frame) => void }> = {
  wave: {
    dur: 1.35,
    apply(t, F) {
      F.squash += kf(t, [[0, 0], [0.16, 0.2, 'out'], [0.3, -0.2, 'out'], [0.55, -0.05], [0.78, 0.04, 'in'], [0.88, 0.22, 'out'], [1.05, -0.06, 'out'], [1.2, 0.02], [1.35, 0]]); // prettier-ignore
      F.lift += kf(t, [
        [0, 0],
        [0.18, 0],
        [0.52, -46, 'out'],
        [0.86, 0, 'in'],
        [1.35, 0],
      ]);
      F.tilt += kf(t, [
        [0, 0],
        [0.3, -8, 'out'],
        [0.6, 8],
        [0.86, 0],
      ]);
      F.happy = Math.max(
        F.happy,
        kf(t, [
          [0, 0],
          [0.2, 1, 'out'],
          [1.05, 1],
          [1.3, 0],
        ]),
      );
    },
  },
  press: {
    dur: 0.55,
    apply(t, F) {
      F.squash += kf(t, [[0, 0], [0.07, 0.24, 'out'], [0.2, -0.12, 'out'], [0.34, 0.05], [0.55, 0]]); // prettier-ignore
      F.open *=
        1 +
        kf(t, [
          [0, 0],
          [0.07, -0.25],
          [0.2, 0.2, 'out'],
          [0.55, 0],
        ]);
    },
  },
  surprise: {
    dur: 1.5,
    apply(t, F) {
      const ant = kf(t, [
        [0, 0],
        [0.12, 1, 'out'],
        [0.22, 0],
      ]);
      const take = kf(t, [
        [0, 0],
        [0.12, 0],
        [0.28, 1, 'back'],
        [1.1, 1],
        [1.5, 0],
      ]);
      F.squash += kf(t, [[0, 0], [0.12, 0.16, 'out'], [0.28, -0.18, 'out'], [0.5, -0.04], [1.5, 0]]); // prettier-ignore
      F.lift += kf(t, [
        [0, 0],
        [0.12, 0],
        [0.28, -14, 'out'],
        [0.55, 0, 'in'],
      ]);
      F.lid = Math.min(1, F.lid + 0.5 * ant);
      F.open = lerp(F.open, 1.45, take);
      F.wide = lerp(F.wide, 1.12, take);
      F.lid *= 1 - take;
      F.happy *= 1 - take;
    },
  },
  think: {
    dur: 2.6,
    apply(t, F) {
      const w = kf(t, [
        [0, 0],
        [0.3, 1, 'out'],
        [2.2, 1],
        [2.6, 0],
      ]);
      F.lookX = lerp(F.lookX, 0.85, w);
      F.lookY = lerp(F.lookY, -0.9, w);
      F.browL = lerp(F.browL, 0.85, w);
      F.browR = lerp(F.browR, -0.8, w);
      F.tilt += 6 * w + 2.5 * Math.sin(t * 5) * w;
    },
  },
  talk: {
    dur: 1.8,
    apply(t, F) {
      const w = kf(t, [
        [0, 0],
        [0.15, 1],
        [1.6, 1],
        [1.8, 0],
      ]);
      const beat = Math.max(0, Math.sin(t * 15)) * Math.abs(Math.sin(t * 3.3));
      F.squash += (0.06 * beat - 0.02) * w;
      F.open *= 1 + 0.08 * beat * w;
      F.lift -= 3 * beat * w;
    },
  },
  nudge: {
    dur: 1.6,
    apply(t, F) {
      F.lift += kf(t, [[0, 0], [0.12, 0], [0.32, -18, 'out'], [0.5, 0, 'in'], [0.62, 0], [0.82, -12, 'out'], [1.0, 0, 'in']]); // prettier-ignore
      F.squash += kf(t, [[0, 0], [0.12, 0.14, 'out'], [0.32, -0.12, 'out'], [0.5, 0.14, 'in'], [0.62, 0.1], [0.82, -0.08, 'out'], [1.0, 0.1, 'in'], [1.2, 0]]); // prettier-ignore
      F.tilt += kf(t, [
        [1.0, 0],
        [1.15, -7],
        [1.3, 6],
        [1.45, -3],
        [1.6, 0],
      ]);
    },
  },
  blink: {
    dur: 0.3,
    apply(t, F) {
      F.blink = Math.max(F.blink, blinkCurve(t));
    },
  },
};

type Spring = { x: number; v: number };
function spring(s: Spring, target: number, k: number, c: number, dt: number): void {
  s.v += (k * (target - s.x) - c * s.v) * dt;
  s.x += s.v * dt;
}

/** One Radi: call `step(dt)` every frame and draw the frame it returns. */
export class Engine {
  rig: Rig;
  t = 0;
  current: Expression = 'idle';
  private from: Expr = { ...EXPR0 };
  private blendT0 = -10;
  private actions: { name: Action; t0: number }[] = [];
  private pointer = { x: 0, y: 0 };
  private hover = false;
  private idle = 0;
  private asleep = false;
  private before: Expression = 'idle';
  private eye = { x: { x: 0, v: 0 }, y: { x: 0, v: 0 } };
  private body = { x: { x: 0, v: 0 }, y: { x: 0, v: 0 } };
  private hov = { x: 0, v: 0 };
  private sq = { x: 0, v: 0 };
  private nextBlink = 1.2;
  private blinkT0 = -10;
  private double = false;
  /** Seconds without the pointer moving before Radi naps; 0 never. */
  sleepAfter = 40;

  constructor(rig: Rig = RIG) {
    this.rig = rig;
  }

  private expr(): Expr {
    const to = { ...EXPR0, ...EXPRESSIONS[this.current] };
    const e = EASE.io(clamp((this.t - this.blendT0) / 0.35, 0, 1));
    const out = { ...EXPR0 };
    for (const k of Object.keys(EXPR0) as (keyof Expr)[]) out[k] = lerp(this.from[k], to[k], e);
    return out;
  }

  setExpression(name: Expression): void {
    if (name === this.current) return;
    this.from = this.expr();
    this.current = name;
    this.blendT0 = this.t;
  }

  play(name: Action): void {
    this.actions.push({ name, t0: this.t });
  }

  setHover(on: boolean): void {
    if (on === this.hover) return;
    this.hover = on;
    this.wake();
    if (on) this.sq.v -= 2.2 * this.rig.squashAmt; // anticipation: dip before growing
  }

  /** Pointer position relative to Radi's center, in drawing units. */
  look(dx: number, dy: number): void {
    const d = Math.hypot(dx, dy) || 1;
    const k = d / (d + 70);
    this.pointer = { x: (dx / d) * k, y: (dy / d) * k };
    this.wake();
  }

  wake(): void {
    this.idle = 0;
    if (this.asleep) {
      this.asleep = false;
      this.setExpression(this.before);
      this.play('surprise');
    }
  }

  step(dt: number): Frame {
    this.t += dt;
    this.idle += dt;
    const R = this.rig;
    const t = this.t;
    if (this.sleepAfter && !this.asleep && this.idle > this.sleepAfter) {
      this.asleep = true;
      this.before = this.current;
      this.setExpression('asleep');
    }
    const F: Frame = {
      ...this.expr(),
      time: t,
      lift: 0,
      blink: 0,
      eyeX: 0,
      eyeY: 0,
      bodyX: 0,
      bodyY: 0,
      hover: 0,
      stretchX: 0,
    };
    F.squash += (F.sleepy ? 0.035 : 0.018) * Math.sin((2 * Math.PI * t) / (F.sleepy ? 4.2 : 3));
    if (!F.sleepy) {
      if (t >= this.nextBlink) {
        this.blinkT0 = t;
        this.double = Math.random() < 0.2;
        this.nextBlink = t + 2 + Math.random() * 3.5;
      }
      let b = blinkCurve(t - this.blinkT0);
      if (this.double) b = Math.max(b, blinkCurve(t - this.blinkT0 - 0.27));
      F.blink = Math.max(F.blink, b);
    }
    this.actions = this.actions.filter((a) => t - a.t0 <= ACTIONS[a.name].dur);
    for (const a of this.actions) ACTIONS[a.name].apply(t - a.t0, F);
    // Eyes reach the pointer first; the body follows later (overlapping action).
    const bounce = clamp(R.bounce, 0, 1);
    const damping = lerp(26, 7, bounce);
    const follow = F.sleepy ? 0 : 1;
    const tx = clamp(this.pointer.x * follow + F.lookX, -1.2, 1.2);
    const ty = clamp(this.pointer.y * follow + F.lookY, -1.2, 1.2);
    if (dt > 0) {
      spring(this.eye.x, tx, 260, damping, dt);
      spring(this.eye.y, ty, 260, damping, dt);
      spring(this.body.x, tx, 70, damping * 0.6, dt);
      spring(this.body.y, ty, 70, damping * 0.6, dt);
      spring(this.hov, this.hover ? 1 : 0, 190, lerp(22, 9, bounce), dt);
      spring(this.sq, 0, 220, lerp(24, 10, bounce), dt);
    }
    F.eyeX = this.eye.x.x;
    F.eyeY = this.eye.y.x;
    F.bodyX = this.body.x.x;
    F.bodyY = this.body.y.x;
    F.hover = this.hov.x;
    F.squash = (F.squash + this.sq.x) * R.squashAmt;
    F.stretchX = clamp(this.body.x.v * 0.012, -0.06, 0.06);
    return F;
  }
}
