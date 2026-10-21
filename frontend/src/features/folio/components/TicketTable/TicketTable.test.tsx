import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DocContent } from '../DocContent';
import { b, doc } from '../DocContent/testDoc';

const ticket = (key: string, title: string, status: string, category: string) => ({
  key,
  title,
  type: 'task',
  status,
  status_category: category,
  priority: 'medium',
  assignee: key === 'PA-1' ? { handle: 'luis', display_name: 'Luis' } : null,
  area: 'Backend',
  milestone: null,
  checklist_done: 0,
  checklist_total: 0,
  url: `/t/${key}`,
});

describe('TicketTable', () => {
  it("lists the query's tickets as Docket shows them to the reader", async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/tickets/query': {
        status: 200,
        body: {
          items: [
            ticket('PA-1', 'Conectar agentes', 'In Progress', 'in_progress'),
            ticket('PA-3', 'Documentar', 'To Do', 'todo'),
          ],
          total: 7,
        },
      },
    });
    const block = b('ticketTable', { rql: 'project = PA', title: 'Pendientes', limit: 2 });
    renderWithProviders(<DocContent doc={doc(block)} />);
    expect(await screen.findByRole('link', { name: 'PA-1' })).toHaveAttribute('href', '/t/PA-1');
    expect(screen.getByText('Conectar agentes')).toBeVisible();
    expect(screen.getByText('@luis')).toBeVisible();
    expect(screen.getByText('Unassigned')).toBeVisible();
    expect(screen.getByText('Showing 2 of 7.')).toBeVisible();
    expect(screen.getByRole('region', { name: 'Pendientes' })).toBeVisible();
    expect(calls[0]?.path).toBe('/api/v1/folio/tickets/query?rql=project%20%3D%20PA&limit=2');
  });

  it("shows why Docket couldn't run the query", async () => {
    mockFetch({
      'GET /api/v1/folio/tickets/query': {
        status: 422,
        body: { status: 422, detail: "Unknown field 'staus'. Did you mean 'status'?", errors: [] },
      },
    });
    renderWithProviders(<DocContent doc={doc(b('ticketTable', { rql: 'staus = Done' }))} />);
    expect(await screen.findByRole('alert')).toHaveTextContent("Did you mean 'status'?");
  });

  it('says so when no ticket the reader can see matches', async () => {
    mockFetch({
      'GET /api/v1/folio/tickets/query': { status: 200, body: { items: [], total: 0 } },
    });
    renderWithProviders(<DocContent doc={doc(b('ticketTable', { rql: 'project = PA' }))} />);
    expect(await screen.findByText(/No tickets you can see/)).toBeVisible();
  });
});
