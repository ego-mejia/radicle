import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAutosave } from './useAutosave';

afterEach(() => vi.useRealTimers());

describe('useAutosave', () => {
  it('saves the latest value once changes stop, and retries after a failure', async () => {
    vi.useFakeTimers();
    const save = vi.fn().mockRejectedValueOnce(new Error('down')).mockResolvedValue(undefined);
    const { result } = renderHook(() => useAutosave(save, 500));
    act(() => {
      result.current.change('a');
      result.current.change('ab');
    });
    expect(result.current.state).toBe('unsaved');
    await act(() => vi.advanceTimersByTimeAsync(500));
    expect(save).toHaveBeenCalledWith('ab');
    expect(result.current.state).toBe('error');
    await act(() => vi.advanceTimersByTimeAsync(500));
    expect(save).toHaveBeenCalledTimes(2);
    expect(result.current.state).toBe('saved');
  });

  it('flush saves right away', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() => useAutosave(save, 10_000));
    act(() => result.current.change('x'));
    await act(() => result.current.flush());
    expect(save).toHaveBeenCalledWith('x');
    expect(result.current.state).toBe('saved');
  });
});
