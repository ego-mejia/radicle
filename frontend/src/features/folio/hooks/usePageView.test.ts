import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { recordView } from '../../../services/api/folioAnalytics';
import { usePageView } from './usePageView';

vi.mock('../../../services/api/folioAnalytics', () => ({ recordView: vi.fn() }));

describe('usePageView', () => {
  beforeEach(() => vi.mocked(recordView).mockReset().mockResolvedValue(undefined));

  it('counts a page once, and again only for another page', () => {
    const { rerender } = renderHook(({ id, on }) => usePageView(id, on), {
      initialProps: { id: 'a', on: true },
    });
    rerender({ id: 'a', on: true });
    expect(recordView).toHaveBeenCalledTimes(1);
    rerender({ id: 'b', on: true });
    expect(vi.mocked(recordView).mock.calls).toEqual([['a'], ['b']]);
  });

  it('waits until the page is published', () => {
    const { rerender } = renderHook(({ on }) => usePageView('a', on), {
      initialProps: { on: false },
    });
    expect(recordView).not.toHaveBeenCalled();
    rerender({ on: true });
    expect(recordView).toHaveBeenCalledWith('a');
  });
});
