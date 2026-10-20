import { describe, expect, it } from 'vitest';
import {
  applyFilters,
  decodeFilters,
  encodeFilters,
  filterCount,
  filtersToRql,
  NO_FILTERS,
} from './listFilters';

describe('list filters', () => {
  it('turns choices into RQL', () => {
    expect(filtersToRql(NO_FILTERS)).toBe('');
    expect(
      filtersToRql({
        ...NO_FILTERS,
        type: ['bug'],
        priority: ['high', 'highest'],
        assignee: ['@me', '@none'],
        area: ['Back end'],
      }),
    ).toBe(
      'type = bug AND priority IN (high, highest) AND (assignee = currentUser() OR assignee IS EMPTY) AND area = "Back end"',
    );
  });

  it('narrows a query and keeps its order', () => {
    const f = { ...NO_FILTERS, type: ['task'] };
    expect(applyFilters('project = PA ORDER BY updated DESC', f)).toBe(
      '(project = PA) AND type = task ORDER BY updated DESC',
    );
    expect(applyFilters('ORDER BY rank', f)).toBe('type = task ORDER BY rank');
    expect(applyFilters('project = PA', NO_FILTERS)).toBe('project = PA');
  });

  it('round-trips through the URL', () => {
    const f = { ...NO_FILTERS, milestone: ['V1'], category: ['todo'] };
    expect(decodeFilters(encodeFilters(f))).toEqual(f);
    expect(encodeFilters(NO_FILTERS)).toBeUndefined();
    expect(decodeFilters('not json')).toEqual(NO_FILTERS);
    expect(filterCount(f)).toBe(2);
  });
});
