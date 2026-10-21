import { act, fireEvent, render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ThemeModeProvider } from '../../../../../../contexts/ThemeModeContext';
import { colorFor, POINTER_IDLE_MS, type Peer } from '../../../../editor/presence';
import { Pointers } from '.';

const ana = (pointer?: Peer['pointer']): Peer => ({
  clientId: 7,
  name: 'Ana Torres',
  handle: 'ana',
  color: colorFor('ana'),
  agent: false,
  pointer,
});

function setup(peers: Peer[]) {
  const container = createRef<HTMLDivElement>();
  const awareness = { setLocalStateField: vi.fn() };
  const view = (list: Peer[]) => (
    <ThemeModeProvider>
      <div ref={container}>
        <Pointers container={container} awareness={awareness} peers={list} />
      </div>
    </ThemeModeProvider>
  );
  const utils = render(view(peers));
  return {
    ...utils,
    awareness,
    container,
    rerenderWith: (list: Peer[]) => utils.rerender(view(list)),
  };
}

afterEach(() => vi.useRealTimers());

describe('Pointers', () => {
  it('shows a pointer with its name and hides it after 10 s still', () => {
    vi.useFakeTimers();
    setup([ana({ x: 40, y: 80, at: 1 }), { ...ana(), clientId: 8 }]);
    expect(screen.getAllByTestId('pointer')).toHaveLength(1);
    expect(screen.getByText('Ana Torres')).toBeInTheDocument();
    expect(screen.getByTestId('pointer').style.transform).toBe('translate(40px, 80px)');
    act(() => vi.advanceTimersByTime(POINTER_IDLE_MS + 1000));
    expect(screen.queryByTestId('pointer')).not.toBeInTheDocument();
  });

  it('shows it again once it moves', () => {
    vi.useFakeTimers();
    const { rerenderWith } = setup([ana({ x: 40, y: 80, at: 1 })]);
    act(() => vi.advanceTimersByTime(POINTER_IDLE_MS + 1000));
    rerenderWith([ana({ x: 60, y: 90, at: 2 })]);
    expect(screen.getByTestId('pointer').style.transform).toBe('translate(60px, 90px)');
  });

  it('sends my pointer at most 30 times a second, and clears it on leave', () => {
    vi.useFakeTimers();
    const { awareness, container } = setup([]);
    const el = container.current!;
    for (let i = 0; i < 10; i++) fireEvent.mouseMove(el, { clientX: 10 + i, clientY: 20 });
    expect(awareness.setLocalStateField).toHaveBeenCalledTimes(1);
    act(() => vi.advanceTimersByTime(40));
    expect(awareness.setLocalStateField).toHaveBeenCalledTimes(2);
    expect(awareness.setLocalStateField).toHaveBeenLastCalledWith(
      'pointer',
      expect.objectContaining({ x: 19, y: 20 }),
    );
    act(() => vi.advanceTimersByTime(40));
    fireEvent.mouseLeave(el);
    expect(awareness.setLocalStateField).toHaveBeenLastCalledWith('pointer', null);
  });
});
