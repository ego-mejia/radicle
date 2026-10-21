import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ticketKeyIn } from '../../../../services/api/folioTickets';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DocContent } from '../DocContent';
import { doc, p, t } from '../DocContent/testDoc';

const TICKET = {
  key: 'PA-4',
  title: 'Conectar agentes',
  type: 'task',
  status: 'In Progress',
  status_category: 'in_progress',
  priority: 'medium',
  assignee: { handle: 'luis', display_name: 'Luis' },
  area: 'Backend',
  milestone: 'V1',
  checklist_done: 1,
  checklist_total: 2,
  url: '/t/PA-4',
};

const ticket = (key: string) => ({ type: 'ticket', attrs: { key } });

describe('TicketChip', () => {
  it('shows live status and assignee, asking once for every chip on the page', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/tickets/preview': {
        status: 200,
        body: {
          items: [
            { key: 'PA-4', restricted: false, ticket: TICKET },
            { key: 'PA-9', restricted: true, ticket: null },
          ],
        },
      },
    });
    renderWithProviders(
      <DocContent doc={doc(p(t('Ver '), ticket('PA-4'), t(' y '), ticket('PA-9')))} />,
    );
    expect(await screen.findByText('Conectar agentes')).toBeVisible();
    expect(screen.getByText('In Progress')).toBeVisible();
    expect(screen.getByText('@luis')).toBeVisible();
    expect(screen.getByRole('link', { name: 'PA-4' })).toHaveAttribute('href', '/t/PA-4');
    expect(screen.getByText('Restricted ticket')).toBeVisible();
    expect(screen.queryByText('PA-9')).not.toBeInTheDocument();
    const asked = calls.filter((c) => c.path.startsWith('/api/v1/folio/tickets/preview'));
    expect(asked.map((c) => c.path)).toEqual(['/api/v1/folio/tickets/preview?keys=PA-4%2CPA-9']);
  });

  it('turns a pasted key or Docket link into a key', () => {
    expect(ticketKeyIn(' pa-4 ')).toBe('PA-4');
    expect(ticketKeyIn('https://radicle.example.com/t/RAD-38')).toBe('RAD-38');
    expect(ticketKeyIn('PA-4 y PA-5')).toBeNull();
    expect(ticketKeyIn('https://radicle.example.com/p/PA/board')).toBeNull();
  });
});
