import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../../../i18n';
import { PROJECT, TICKET } from '../../../../test/fixtures';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { TicketDetail } from '.';

describe('TicketDetail', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('shows a version conflict and reloads without losing the draft', async () => {
    let current = TICKET;
    const calls = mockFetch({
      'GET /api/v1/tickets/PA-4': () => ({ status: 200, body: current }),
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
      'GET /api/v1/tickets/PA-4/comments': { status: 200, body: { items: [], next_cursor: null } },
      'PATCH /api/v1/tickets/PA-4': (_req, body) => {
        expect((body as { expected_version: number }).expected_version).toBe(3);
        current = { ...TICKET, title: 'Changed elsewhere', version: 4 };
        return {
          status: 409,
          body: {
            status: 409,
            detail: 'Someone else changed PA-4',
            errors: [],
            current_version: 4,
          },
        };
      },
    });
    renderWithProviders(<TicketDetail ticketKey="PA-4" />);
    await userEvent.click(await screen.findByRole('button', { name: 'Edit title' }));
    const input = screen.getByRole('textbox', { name: 'Title' });
    await userEvent.clear(input);
    await userEvent.type(input, 'My title{Enter}');

    expect(await screen.findByText('Someone else changed this ticket.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Reload and keep my text' }));
    await waitFor(() =>
      expect(screen.queryByText('Someone else changed this ticket.')).not.toBeInTheDocument(),
    );
    expect(screen.getByRole('heading', { name: 'Changed elsewhere' })).toBeInTheDocument();
    expect(calls.filter((c) => c.method === 'PATCH')).toHaveLength(1);
  });

  it('toggles a checklist item through the API', async () => {
    const calls = mockFetch({
      'GET /api/v1/tickets/PA-4': { status: 200, body: TICKET },
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
      'GET /api/v1/tickets/PA-4/comments': { status: 200, body: { items: [], next_cursor: null } },
      'PATCH /api/v1/tickets/PA-4/checklist/1': { status: 200, body: { ...TICKET, version: 4 } },
    });
    renderWithProviders(<TicketDetail ticketKey="PA-4" />);
    const boxes = await screen.findAllByRole('checkbox');
    await userEvent.click(boxes[1]!);
    await waitFor(() =>
      expect(calls).toContainEqual({
        method: 'PATCH',
        path: '/api/v1/tickets/PA-4/checklist/1',
        body: { checked: true },
      }),
    );
  });
});
