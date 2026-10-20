import { render } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { lightTheme } from '../../../../../../styles/theme';
import { Confetti } from '.';

function fakeContext() {
  const calls: string[] = [];
  const record = (name: string) => () => calls.push(name);
  const ctx = new Proxy({} as Record<string, unknown>, {
    get: (target, key: string) => (key in target ? target[key] : record(key)),
    set: (target, key: string, value) => ((target[key] = value), true),
  });
  return { ctx, calls };
}

describe('Confetti', () => {
  afterEach(() => vi.restoreAllMocks());

  it('throws pieces in the theme colors and cleans up', () => {
    const { ctx, calls } = fakeContext();
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(ctx as never);
    let tick: FrameRequestCallback = () => {};
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => ((tick = cb), 1));
    const cancel = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
    const { container, unmount } = render(
      <ThemeProvider theme={lightTheme}>
        <Confetti />
      </ThemeProvider>,
    );
    expect(container.querySelector('canvas')).toHaveAttribute('aria-hidden', 'true');
    tick(16);
    tick(32);
    expect(calls.filter((c) => c === 'fillRect').length).toBeGreaterThan(100);
    unmount();
    expect(cancel).toHaveBeenCalled();
  });
});
