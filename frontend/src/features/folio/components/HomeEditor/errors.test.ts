import { describe, expect, it } from 'vitest';
import { ApiError } from '../../../../services/api/client';
import { blockErrors } from './errors';

const BLOCKS = [
  { id: 'hero', type: 'featured', x: 0, y: 0, w: 7, h: 4, config: {} },
  { id: 'q', type: 'query', x: 7, y: 0, w: 5, h: 4, config: {} },
];

function problem(status: number, errors: { field?: string; message: string; position?: number }[]) {
  return new ApiError({ type: 'about:blank', title: '', status, detail: 'bad', errors });
}

describe('blockErrors', () => {
  it('files each 422 error under its block, with the field and RQL position', () => {
    const found = blockErrors(
      problem(422, [
        { field: 'blocks[1].config.rql', message: 'Unknown field', position: 3 },
        { field: 'blocks[0]', message: 'Must fit' },
        { field: 'blocks', message: 'Too many' },
      ]),
      BLOCKS,
    );
    expect(found.get('q')).toEqual([
      { field: 'config.rql', message: 'Unknown field', position: 3 },
    ]);
    expect(found.get('hero')).toEqual([{ field: '', message: 'Must fit', position: undefined }]);
    expect(found.size).toBe(2);
  });

  it('ignores anything that is not a 422', () => {
    expect(blockErrors(problem(409, []), BLOCKS).size).toBe(0);
    expect(blockErrors(new Error('offline'), BLOCKS).size).toBe(0);
  });
});
