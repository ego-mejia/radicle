import { describe, expect, it } from 'vitest';
import { filtersToSearch } from './filtersToSearch';

describe('filtersToSearch', () => {
  it('turns filters into a link', () => {
    expect(filtersToSearch({ project: 'RAD', features: ['A', 'B'], status: 'done' })).toBe(
      'project=RAD&feature=A&feature=B&status=done',
    );
    expect(filtersToSearch({ features: [] })).toBe('');
  });
});
