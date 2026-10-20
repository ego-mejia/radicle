import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PROJECT, TICKET } from '../../../../test/fixtures';
import type { TicketSummary } from '../../../../services/api/types';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { FlashContext, useFlash } from '../../hooks/flash';
import { TicketCard } from '.';

function Card({ ticketKey }: { ticketKey: string }) {
  return (
    <TicketCard
      ticket={{ ...TICKET, key: ticketKey } as unknown as TicketSummary}
      flash={useFlash(ticketKey)}
    />
  );
}

describe('TicketCard flash', () => {
  it('flashes only the card that moved, brighter when it is done', async () => {
    renderWithProviders(
      <FlashContext.Provider value={{ key: 'PA-2', kind: 'done' }}>
        <Card ticketKey="PA-1" />
        <Card ticketKey="PA-2" />
      </FlashContext.Provider>,
    );
    expect(await screen.findByLabelText(/^PA-1 /)).not.toHaveAttribute('data-flash');
    expect(screen.getByLabelText(/^PA-2 /)).toHaveAttribute('data-flash', 'done');
  });
});

describe('TicketCard chips', () => {
  const project = {
    ...PROJECT,
    areas: [
      { name: 'Backend', color: '#2563EB', icon: 'server', position: 0, archived: false },
      { name: 'Mobile', color: '#DB2777', icon: null, position: 1, archived: false },
    ],
    milestones: [{ name: 'Beta', status: 'open' }],
  };
  const ticket = {
    ...TICKET,
    area: 'Backend',
    milestone: null,
    child_count: 3,
  } as unknown as TicketSummary;

  it('shows area, milestone and subtickets, and changes the area from its menu', async () => {
    const calls = mockFetch({
      'GET /api/v1/projects/PA': { status: 200, body: project },
      'GET /api/v1/tickets/PA-4': { status: 200, body: { ...TICKET, version: 7 } },
      'PATCH /api/v1/tickets/PA-4': { status: 200, body: TICKET },
    });
    const onOpen = vi.fn();
    renderWithProviders(<TicketCard ticket={ticket} onClick={onOpen} />);
    expect(await screen.findByTitle('3 subtickets')).toHaveTextContent('3');
    const area = await screen.findByRole('button', { name: 'Backend' });
    expect(screen.getByRole('button', { name: 'Milestone' })).toHaveAttribute('data-empty');

    await userEvent.click(area);
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Mobile' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true));
    expect(calls.find((c) => c.method === 'PATCH')!.body).toEqual({
      area: 'Mobile',
      expected_version: 7,
    });
    expect(onOpen).not.toHaveBeenCalled();
  });

  it('only shows the chips without the right to edit', async () => {
    mockFetch({
      'GET /api/v1/projects/PA': {
        status: 200,
        body: { ...project, milestones: [], permissions: [] },
      },
    });
    renderWithProviders(<TicketCard ticket={{ ...ticket, milestone: 'Beta' }} />);
    expect(await screen.findByText('Backend')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Backend' })).toBeNull());
  });
});
