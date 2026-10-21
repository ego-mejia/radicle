import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useFocusMode } from './useFocusMode';

describe('useFocusMode', () => {
  beforeEach(() => localStorage.clear());

  it('remembers the choice per user', () => {
    const { result } = renderHook(() => useFocusMode('luis'));
    expect(result.current[0]).toBe(false);
    act(() => result.current[1](true));
    expect(result.current[0]).toBe(true);
    expect(renderHook(() => useFocusMode('luis')).result.current[0]).toBe(true);
    expect(renderHook(() => useFocusMode('ana')).result.current[0]).toBe(false);
    act(() => result.current[1](false));
    expect(renderHook(() => useFocusMode('luis')).result.current[0]).toBe(false);
  });

  it('still toggles when storage is blocked', () => {
    const blocked = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    const { result } = renderHook(() => useFocusMode('luis'));
    expect(result.current[0]).toBe(false);
    act(() => result.current[1](true));
    expect(result.current[0]).toBe(true);
    blocked.mockRestore();
    vi.restoreAllMocks();
  });
});
