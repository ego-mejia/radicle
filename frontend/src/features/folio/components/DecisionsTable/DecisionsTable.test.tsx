import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DecisionsTable } from '.';

const decision = (n: number, title: string, extra: Record<string, unknown> = {}) => ({
  node: {
    id: `00000000-0000-0000-0000-00000000000${n}`,
    kind: 'page',
    title,
    slug: `adr-${n}`,
    icon: null,
    status: 'published',
  },
  number: n,
  description: `${title}.`,
  topic: 'Datos',
  project: 'RAD',
  status: 'accepted',
  replaces: null,
  replaced_by: null,
  published_at: '2026-10-21T10:00:00Z',
  ...extra,
});

const LIST = {
  items: [
    decision(3, 'pgvector para la búsqueda', { replaces: 1 }),
    decision(2, 'Plugins sin servidor', { topic: 'Arquitectura', status: 'proposed' }),
  ],
  total: 2,
  hidden_replaced: 1,
  topics: [
    { value: 'Datos', count: 2 },
    { value: 'Arquitectura', count: 1 },
  ],
  projects: [{ value: 'RAD', count: 3 }],
};

describe('DecisionsTable', () => {
  it('lists current decisions with their number, topic and what they replace', async () => {
    mockFetch({ 'GET /api/v1/folio/spaces/ing/decisions': { status: 200, body: LIST } });
    renderWithProviders(<DecisionsTable space="ing" />);
    const row = (await screen.findByRole('link', { name: 'pgvector para la búsqueda' })).closest(
      'tr',
    )!;
    expect(within(row).getByText('0003')).toBeInTheDocument();
    expect(within(row).getByText('0001')).toBeInTheDocument();
    expect(within(row).getByText('Accepted')).toBeInTheDocument();
    expect(screen.getByText('In discussion')).toBeInTheDocument();
    expect(screen.getByText('1 replaced decision hidden')).toBeInTheDocument();
  });

  it('shows replaced ones when asked, and filters by topic', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/spaces/ing/decisions': (req) => {
        const status = new URL(req.url).searchParams.get('status');
        const items =
          status === 'all'
            ? [...LIST.items, decision(1, 'Solo texto', { status: 'replaced', replaced_by: 3 })]
            : LIST.items;
        return { status: 200, body: { ...LIST, items, total: items.length } };
      },
    });
    renderWithProviders(<DecisionsTable space="ing" />);
    await userEvent.click(await screen.findByRole('button', { name: 'Status: Current' }));
    await userEvent.click(screen.getByRole('menuitemradio', { name: 'All' }));
    expect(await screen.findByText('Replaced by 0003')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Topic: All' }));
    await userEvent.click(screen.getByRole('menuitemradio', { name: /Arquitectura/ }));
    expect(calls.at(-1)?.path).toContain('topic=Arquitectura');
    expect(screen.getByRole('button', { name: 'Remove Arquitectura' })).toBeInTheDocument();
  });

  it('says when the space has no decisions yet', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces/ing/decisions': {
        status: 200,
        body: { ...LIST, items: [], total: 0, hidden_replaced: 0 },
      },
    });
    renderWithProviders(<DecisionsTable space="ing" />);
    expect(await screen.findByText(/No architecture decisions here yet/)).toBeInTheDocument();
  });
});
