import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { BuildSpecTickets } from '.';

const NODE = '11111111-1111-1111-1111-111111111111';
const PROJECT = {
  key: 'PA',
  name: 'ProyectoA',
  archived: false,
  areas: [{ name: 'Backend', archived: false }],
  milestones: [{ name: 'V1', status: 'open' }],
};
const item = (key: string, title: string, extra: object = {}) => ({
  key,
  title,
  description: '',
  criteria: ['Uno', 'Dos'],
  anchor: 'entregables',
  linked: false,
  restricted: false,
  ticket: null,
  ...extra,
});
const ITEMS = [
  item('4.1', 'Tickets dentro de los docs', {
    linked: true,
    ticket: { key: 'PA-3', status: 'To Do' },
  }),
  item('4.2', 'Crear ticket desde texto'),
  item('4.3', 'Build spec a tickets', { criteria: ['Sale'] }),
];

function mocks(post: { status: number; body: unknown }) {
  return mockFetch({
    'GET /api/v1/projects': { status: 200, body: { items: [PROJECT] } },
    'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
    [`GET /api/v1/folio/nodes/${NODE}/build-spec/items`]: {
      status: 200,
      body: { items: ITEMS },
    },
    [`POST /api/v1/folio/nodes/${NODE}/build-spec/tickets`]: post,
  });
}

describe('BuildSpecTickets', () => {
  it('sends the chosen new deliverables to Docket', async () => {
    const calls = mocks({ status: 201, body: { items: [ITEMS[1]] } });
    renderWithProviders(<BuildSpecTickets nodeId={NODE} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Create tickets' }));
    const sent = await screen.findByRole('checkbox', { name: '4.1 Tickets dentro de los docs' });
    expect(sent).toBeDisabled();
    expect(screen.getByText('Already PA-3')).toBeVisible();
    expect(screen.getByText('1 criterion')).toBeVisible();
    await userEvent.click(screen.getByRole('checkbox', { name: '4.3 Build spec a tickets' }));
    await screen.findByRole('option', { name: 'Backend' });
    await userEvent.selectOptions(screen.getByLabelText(/^Area/), 'Backend');
    await userEvent.click(screen.getByRole('button', { name: 'Create 1 ticket' }));
    expect(await screen.findByText('1 ticket created and linked.')).toBeVisible();
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      project: 'PA',
      keys: ['4.2'],
      type: 'task',
      area: 'Backend',
      milestone: null,
    });
  });

  it("shows Docket's reason when it refuses", async () => {
    mocks({
      status: 422,
      body: { status: 422, detail: 'Area is required for task tickets.', errors: [] },
    });
    renderWithProviders(<BuildSpecTickets nodeId={NODE} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Create tickets' }));
    await screen.findByRole('option', { name: 'PA · ProyectoA' });
    await userEvent.click(await screen.findByRole('button', { name: 'Create 2 tickets' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Area is required');
  });
});
