import { describe, expect, it } from 'vitest';
import * as Y from 'yjs';
import { elementsOf, merge, pushLocal, wins, type SceneElement } from './sync';

const el = (id: string, version: number, extra: Partial<SceneElement> = {}): SceneElement => ({
  id,
  type: 'rectangle',
  version,
  versionNonce: 5,
  index: 'a0',
  ...extra,
});

/** Two docs that exchange updates as the room would. */
function pair(): [Y.Doc, Y.Doc] {
  const a = new Y.Doc();
  const b = new Y.Doc();
  a.on('update', (u: Uint8Array) => Y.applyUpdate(b, u, 'remote'));
  b.on('update', (u: Uint8Array) => Y.applyUpdate(a, u, 'remote'));
  return [a, b];
}

describe('whiteboard sync', () => {
  it('the higher version wins, and on a tie the lower nonce', () => {
    expect(wins(el('x', 2), el('x', 1))).toBe(true);
    expect(wins(el('x', 1), el('x', 2))).toBe(false);
    expect(wins(el('x', 1, { versionNonce: 1 }), el('x', 1, { versionNonce: 9 }))).toBe(true);
    expect(wins(el('x', 1), el('x', 1))).toBe(false);
    expect(wins(el('x', 1), undefined)).toBe(true);
  });

  it('writes only what changed', () => {
    const doc = new Y.Doc();
    expect(pushLocal(doc, [el('a', 1), el('b', 1)])).toBe(2);
    expect(pushLocal(doc, [el('a', 1), el('b', 2)])).toBe(1);
    expect(elementsOf(doc).get('b')?.version).toBe(2);
    expect(pushLocal(doc, [el('a', 1)])).toBe(0); // an echo of what came in
  });

  it('two people drawing end with the same scene', () => {
    const [a, b] = pair();
    pushLocal(a, [el('box', 1, { index: 'a1' })]);
    pushLocal(b, [el('note', 1, { index: 'a0', type: 'text' })]);
    pushLocal(b, [el('box', 2, { index: 'a1', x: 40 })]);
    const sceneA = merge([], elementsOf(a).values());
    const sceneB = merge([], elementsOf(b).values());
    expect(sceneA).toEqual(sceneB);
    expect(sceneA.map((e) => e.id)).toEqual(['note', 'box']);
    expect(sceneA[1]?.x).toBe(40);
  });

  it('keeps local edits that are newer than the shared map', () => {
    const scene = merge(
      [el('a', 3, { x: 1 })],
      [el('a', 2, { x: 9 }), el('b', 1, { index: 'b0' })],
    );
    expect(scene.map((e) => [e.id, e.version])).toEqual([
      ['a', 3],
      ['b', 1],
    ]);
  });
});
