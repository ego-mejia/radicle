import { fireEvent, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { TicketSummary } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { GroupedRows } from '.';

const ticket = (key: string, extra: Partial<TicketSummary> = {}) =>
  ({
    key,
    type: 'task',
    title: `Ticket ${key}`,
    status: { name: 'To Do', category: 'todo' },
    priority: 'medium',
    vote_count: 0,
    assignee: null,
    area: 'Backend',
    milestone: null,
    due_date: null,
    blocked: false,
    updated_at: '2026-10-01T10:00:00Z',
    parent: null,
    child_count: 0,
    ...extra,
  }) as unknown as TicketSummary;

vi.mock('../../../../services/api/tickets', async (original) => ({
  ...(await original<typeof import('../../../../services/api/tickets')>()),
  fetchChildren: () => Promise.resolve([ticket('PA-9', { parent: 'PA-1', type: 'bug' })]),
}));

describe('GroupedRows', () => {
  it('groups rows and opens subtickets under their parent', async () => {
    renderWithProviders(
      <table>
        <GroupedRows
          tickets={[
            ticket('PA-1', { child_count: 2 }),
            ticket('PA-2', { parent: 'PA-1' }),
            ticket('PA-3', { area: 'Mobile' }),
          ]}
          groupBy="area"
          nest
          columns={11}
          onOpen={() => {}}
        />
      </table>,
    );
    const backend = await screen.findByRole('button', { name: /Backend/ });
    expect(screen.queryByText('Ticket PA-2')).not.toBeInTheDocument(); // nested under PA-1
    const open = screen.getByRole('button', { name: '2 subtickets of PA-1' });
    fireEvent.click(open);
    expect(await screen.findByText('Ticket PA-9')).toBeInTheDocument();
    fireEvent.click(backend);
    expect(screen.queryByText('Ticket PA-1')).not.toBeInTheDocument();
    const mobile = screen.getByRole('button', { name: /Mobile/ });
    expect(within(mobile).getByText('1')).toBeInTheDocument();
  });
});
