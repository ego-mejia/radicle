import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { makeClient, mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DocContent } from '../DocContent';

const NODE = '11111111-1111-1111-1111-111111111111';
const ticket = (key: string, status: string, category: string, done: number) => ({
  key,
  title: 'x',
  type: 'task',
  status,
  status_category: category,
  priority: 'medium',
  assignee: { handle: 'luis', display_name: 'Luis' },
  area: 'Backend',
  milestone: 'V1',
  checklist_done: done,
  checklist_total: 2,
  url: `/t/${key}`,
});
const item = (key: string, title: string, extra: object) => ({
  key,
  title,
  description: '',
  criteria: [],
  anchor: 'entregables',
  linked: false,
  restricted: false,
  ticket: null,
  ...extra,
});
const doc = {
  type: 'doc',
  content: [{ type: 'ticketProgress', attrs: { title: 'Avance de la fase' } }],
};

describe('TicketProgress', () => {
  it("shows each deliverable's ticket, live", async () => {
    mockFetch({
      [`GET /api/v1/folio/nodes/${NODE}/build-spec/items`]: {
        status: 200,
        body: {
          items: [
            item('4.1', 'Tickets en docs', {
              linked: true,
              ticket: ticket('PA-1', 'Done', 'done', 2),
            }),
            item('4.2', 'Desde texto', {
              linked: true,
              ticket: ticket('PA-2', 'In Progress', 'in_progress', 1),
            }),
            item('4.3', 'Build spec', {}),
            item('4.4', 'Secreto', { linked: true, restricted: true }),
          ],
        },
      },
    });
    renderWithProviders(<DocContent doc={doc} />, makeClient(), `/folio/p/${NODE}-fase-4/edit`);
    const box = await screen.findByRole('region', { name: 'Avance de la fase' });
    expect(await screen.findByText('1 of 4 done')).toBeVisible();
    expect(box).toHaveTextContent('PA-2');
    expect(screen.getByRole('progressbar', { name: 'Checklist of PA-2' })).toHaveTextContent('1/2');
    expect(screen.getByText('No ticket yet')).toBeVisible();
    expect(screen.getByText('Restricted ticket')).toBeVisible();
  });

  it('asks to be on the build spec page elsewhere', async () => {
    renderWithProviders(<DocContent doc={doc} />);
    expect(await screen.findByText("Shows on the build spec's own page.")).toBeVisible();
  });

  it('says why when the doc is not a build spec', async () => {
    mockFetch({
      [`GET /api/v1/folio/nodes/${NODE}/build-spec/items`]: {
        status: 422,
        body: { status: 422, detail: 'Only build-spec docs have deliverables.', errors: [] },
      },
    });
    renderWithProviders(<DocContent doc={doc} />, makeClient(), `/folio/p/${NODE}-fase-4/edit`);
    expect(await screen.findByRole('alert')).toHaveTextContent('Only build-spec docs');
  });
});
