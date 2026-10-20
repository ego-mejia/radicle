import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { TicketSummary } from '../../services/api/types';
import { renderWithProviders } from '../../test/renderWithProviders';
import { TicketTable } from '.';

const ticket = (n: number) =>
  ({
    key: `PA-${n}`,
    type: 'task',
    title: `Ticket ${n}`,
    status: { name: 'To Do', category: 'todo' },
    priority: 'medium',
    vote_count: 0,
    assignee: null,
    area: 'Backend',
    milestone: null,
    due_date: null,
    blocked: false,
    updated_at: '2026-10-01T10:00:00Z',
  }) as unknown as TicketSummary;

describe('TicketTable', () => {
  it('lines every row up with the header', async () => {
    renderWithProviders(
      <TicketTable
        tickets={[ticket(1), ticket(2)]}
        total={2}
        onOpen={() => {}}
        hasMore={false}
        loadingMore={false}
        onLoadMore={() => {}}
      />,
    );
    const table = await screen.findByRole('table');
    expect(table.querySelectorAll('tbody')).toHaveLength(1);
    const [header, ...rows] = within(table).getAllByRole('row');
    expect(rows).toHaveLength(2);
    const columns = within(header!).getAllByRole('columnheader').length;
    for (const row of rows) expect(within(row).getAllByRole('cell')).toHaveLength(columns);
  });
});
