import { describe, expect, it } from 'vitest';
import type { HomeLayoutBlock } from '../../../../services/api/folio';
import { addBlock, applyPlacements, isDirty, removeBlock, setConfig } from './state';

const HERO: HomeLayoutBlock = {
  id: 'featured',
  type: 'featured',
  x: 0,
  y: 0,
  w: 7,
  h: 4,
  config: { node: null },
};

describe('home editor state', () => {
  it('adds a block under the others with an id of its own', () => {
    const one = addBlock([HERO], 'featured');
    expect(one[1]).toEqual({
      id: 'featured-2',
      type: 'featured',
      x: 0,
      y: 4,
      w: 7,
      h: 4,
      config: {},
    });
    const two = addBlock(one, 'most_read');
    expect(two[2]).toMatchObject({ id: 'most-read', y: 8, w: 6 });
  });

  it('keeps what the grid did after a drag or a resize', () => {
    const blocks = addBlock([HERO], 'text');
    const moved = applyPlacements(blocks, [
      { i: 'featured', x: 0, y: 0, w: 7, h: 4 },
      { i: 'text', x: 7, y: 0, w: 5, h: 20 },
    ]);
    expect(moved[0]).toBe(blocks[0]);
    expect(moved[1]).toMatchObject({ x: 7, y: 0, w: 5, h: 12 });
    expect(isDirty(blocks, moved)).toBe(true);
    expect(isDirty(blocks, applyPlacements(blocks, []))).toBe(false);
  });

  it('changes a block config and removes blocks', () => {
    const blocks = setConfig([HERO], 'featured', { node: 'n1' });
    expect(blocks[0]?.config).toEqual({ node: 'n1' });
    expect(removeBlock(blocks, 'featured')).toEqual([]);
  });
});
