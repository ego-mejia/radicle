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

  it('draws each eye as one path, half moons included', () => {
    const radi = new Engine();
    radi.setExpression('happy');
    const svg = renderRadi(radi.rig, run(radi, 1));
    expect(svg.match(/<path d="M[^"]+" fill="#FFFFFF"/g)).toHaveLength(2);
    expect(svg).not.toContain('<mask');
  });

  it('turns his head, so the far eye narrows', () => {
    const width = (svg: string, eye: number) => {
      const eyes = svg.match(/<path d="M[^"]+" fill="#FFFFFF"/g)!;
      const xs = eyes[eye]!.match(/[\d.]+(?= )/g)!.map(Number);
      return Math.max(...xs) - Math.min(...xs);
    };
    const radi = new Engine();
    radi.look(400, 0);
    const svg = renderRadi(radi.rig, run(radi, 2));
    // Looking right turns the right eye away from the viewer.
    expect(width(svg, 1)).toBeLessThan(width(svg, 0) * 0.7);
  });
});
