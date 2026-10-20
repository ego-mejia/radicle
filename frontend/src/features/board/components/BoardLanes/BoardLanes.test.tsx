import { DndContext } from '@dnd-kit/core';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import type { BoardData } from '../../../../services/api/types';
import { PROJECT } from '../../../../test/fixtures';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
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
    project: 'PA',
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

  it('shows each area lane with its icon in its color', async () => {
    mockFetch({
      'GET /api/v1/projects/PA': {
        status: 200,
        body: {
          ...PROJECT,
          areas: [
            { name: 'Backend', color: '#2563EB', icon: 'server', position: 0, archived: false },
          ],
        },
      },
    });
    renderWithProviders(
      <DndContext>
        <BoardLanes data={data} columnState={() => 'idle'} canDrag onOpen={() => {}} />
      </DndContext>,
    );
    const backend = await screen.findByRole('button', { name: /Backend/ });
    // The chevron plus the server icon; Mobile has no icon, so only its chevron is an svg.
    await waitFor(() => expect(backend.querySelectorAll('svg')).toHaveLength(2));
    expect(screen.getByRole('button', { name: /Mobile/ }).querySelectorAll('svg')).toHaveLength(1);
  });
});
