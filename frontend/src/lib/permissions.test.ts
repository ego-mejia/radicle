import { describe, expect, it } from 'vitest';
import { can } from './permissions';

describe('can', () => {
  it('reads the permission list and respects archived projects', () => {
    expect(can({ permissions: ['vote'] }, 'vote')).toBe(true);
    expect(can({ permissions: ['vote'] }, 'ticket.edit')).toBe(false);
    expect(can({ permissions: ['vote'], archived: true }, 'vote')).toBe(false);
    expect(can(undefined, 'vote')).toBe(false);
  });
});
