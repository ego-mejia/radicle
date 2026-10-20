import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core';
import { act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { BoardData, TransitionOption } from '../../../services/api/types';
import { renderWithProviders } from '../../../test/renderWithProviders';
import { placeCard, useBoardDrag } from './useBoardDrag';

const moveCard = vi.fn();
let resolveTransitions: (options: TransitionOption[]) => void = () => {};

vi.mock('../../../services/api/boards', () => ({
  moveCard: (...args: unknown[]) => moveCard(...args),
}));
vi.mock('../../../services/api/tickets', async (original) => ({
  ...(await original<typeof import('../../../services/api/tickets')>()),
  fetchTransitions: () => new Promise((resolve) => (resolveTransitions = resolve)),
}));

const card = { key: 'PA-1', type: 'task', title: 'A card' };
const data = {
  board: {
    id: 'b1',
    statuses: [],
    columns: [
      { name: 'To Do', categories: ['todo'], status_ids: [] },
      { name: 'In Progress', categories: ['in_progress'], status_ids: [] },
    ],
  },
  columns: [
    { index: 0, tickets: [] },
    { index: 1, tickets: [card] },
  ],
} as unknown as BoardData;
const backToTodo = {
  name: 'Stop',
  to_status: 'To Do',
  category: 'todo',
  available: true,
  requires_comment: false,
  has_screen: false,
  allowed_resolutions: null,
} as unknown as TransitionOption;

let hook: ReturnType<typeof useBoardDrag>;
function Probe() {
  hook = useBoardDrag(data, 'PA', ['tickets', 'board', 'b1', {}]);
  return null;
}

describe('useBoardDrag', () => {
  beforeEach(() => {
    moveCard.mockReset().mockResolvedValue({ ticket: card, warnings: [] });
  });

  it('moves a card dropped before its transitions arrive', async () => {
    renderWithProviders(<Probe />);
    await waitFor(() => expect(hook).toBeDefined());
    act(() => {
      void hook.onDragStart({
        active: { data: { current: { ticket: card } } },
      } as unknown as DragStartEvent);
    });
    let drop: Promise<void> = Promise.resolve();
    act(() => {
      drop = hook.onDragEnd({
        over: { data: { current: { column: 0 } } },
      } as unknown as DragEndEvent);
    });
    expect(moveCard).not.toHaveBeenCalled();
    await act(async () => {
      resolveTransitions([backToTodo]);
      await drop;
    });
    await waitFor(() =>
      expect(moveCard).toHaveBeenCalledWith(
        'b1',
        expect.objectContaining({ ticket: 'PA-1', column: 0, transition: 'Stop' }),
      ),
    );
  });
});

describe('placeCard', () => {
  const board = (cols: string[][]) =>
    ({
      columns: cols.map((keys, index) => ({
        index,
        count: keys.length,
        tickets: keys.map((key) => ({ key })),
      })),
    }) as unknown as BoardData;
  const keys = (b: BoardData) => b.columns.map((c) => c.tickets.map((t) => t.key));

  it('drops the card right where it was let go', () => {
    const b = board([
      ['A', 'B'],
      ['C', 'D', 'E'],
    ]);
    expect(keys(placeCard(b, 'A', 1, { before: 'D', after: null }))).toEqual([
      ['B'],
      ['C', 'A', 'D', 'E'],
    ]);
    expect(keys(placeCard(b, 'A', 1, { before: null, after: 'D' }))).toEqual([
      ['B'],
      ['C', 'D', 'A', 'E'],
    ]);
    expect(keys(placeCard(b, 'A', 1, { before: null, after: null }))).toEqual([
      ['B'],
      ['C', 'D', 'E', 'A'],
    ]);
    const moved = placeCard(b, 'A', 1, { before: 'C', after: null });
    expect(moved.columns.map((c) => c.count)).toEqual([1, 4]);
  });

  it('reorders inside a column', () => {
    const b = board([['A', 'B', 'C']]);
    expect(keys(placeCard(b, 'C', 0, { before: 'A', after: null }))).toEqual([['C', 'A', 'B']]);
  });
});
