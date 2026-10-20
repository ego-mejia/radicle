import { describe, expect, it } from 'vitest';
import { Engine, kf } from './engine';
import { renderRadi } from './render';

const run = (engine: Engine, seconds: number) => {
  let frame = engine.step(0);
  for (let t = 0; t < seconds; t += 1 / 60) frame = engine.step(1 / 60);
  return frame;
};

describe('Radi engine', () => {
  it('eases between keys', () => {
    expect(
      kf(0.5, [
        [0, 0],
        [1, 10],
      ]),
    ).toBe(5);
    expect(
      kf(2, [
        [0, 0],
        [1, 10],
      ]),
    ).toBe(10);
  });

  it('looks toward the pointer, eyes before body', () => {
    const radi = new Engine();
    radi.look(300, -200);
    const early = run(radi, 0.08);
    expect(early.eyeX).toBeGreaterThan(early.bodyX);
    const settled = run(radi, 2);
    expect(settled.eyeX).toBeGreaterThan(0.5);
    expect(settled.eyeY).toBeLessThan(0);
  });

  it('grows and opens his eyes when hovered', () => {
    const radi = new Engine();
    radi.setHover(true);
    expect(run(radi, 1.5).hover).toBeCloseTo(1, 1);
  });

  it('thinks with one brow down and naps when nobody moves', () => {
    const radi = new Engine();
    radi.setExpression('thinking');
    const thinking = run(radi, 1);
    expect(thinking.browL).toBeGreaterThan(0.5);
    expect(thinking.browR).toBeLessThan(-0.5);
    expect(renderRadi(radi.rig, thinking)).toContain('rotate(');
    radi.sleepAfter = 1;
    expect(run(radi, 2).sleepy).toBeGreaterThan(0.9);
    radi.look(10, 10);
    expect(radi.current).toBe('thinking');
  });

  it('draws happy eyes as half moons', () => {
    const radi = new Engine();
    radi.setExpression('happy');
    const svg = renderRadi(radi.rig, run(radi, 1));
    expect(svg.match(/<mask /g)).toHaveLength(2);
    expect(svg).toContain('fill="#000"');
  });
});
