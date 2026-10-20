import { DndContext } from '@dnd-kit/core';
import { fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import type { BoardData } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { BoardLanes } from '.';

const card = (key: string, lane: string) => ({
  key,
  lane,
  type: 'task',
  title: `Ticket ${key}`,
  status: { name: 'To Do', category: 'todo' },
  priority: 'medium',
  tags: [],
  blocked: false,
  checklist_total: 0,
  vote_count: 0,
  assignee: null,
});
const data = {
  board: {
    id: 'b1',
    statuses: [],
    columns: [{ name: 'To Do', categories: ['todo'], status_ids: [] }],
  },
  swimlane_by: 'area',
  columns: [
    { index: 0, name: 'To Do', count: 2, tickets: [card('PA-1', 'a1'), card('PA-2', 'a2')] },
  ],
  lanes: [
    { key: 'a1', label: 'Backend', count: 1 },
    { key: 'a2', label: 'Mobile', count: 1 },
  ],
} as unknown as BoardData;

describe('BoardLanes', () => {
  beforeEach(() => localStorage.clear());

  it('hides a lane, collapses all and remembers it', async () => {
    const view = () =>
      renderWithProviders(
        <DndContext>
          <BoardLanes data={data} columnState={() => 'idle'} canDrag onOpen={() => {}} />
        </DndContext>,
      );
    const first = view();
    fireEvent.click(await screen.findByRole('button', { name: /Backend/ }));
    expect(screen.queryByText('Ticket PA-1')).not.toBeInTheDocument();
    expect(screen.getByText('Ticket PA-2')).toBeInTheDocument();
    first.unmount();
    view();
    expect(await screen.findByText('Ticket PA-2')).toBeInTheDocument();
    expect(screen.queryByText('Ticket PA-1')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Collapse all' }));
    expect(screen.queryByText('Ticket PA-2')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Expand all' }));
    expect(screen.getByText('Ticket PA-1')).toBeInTheDocument();
  });
});
