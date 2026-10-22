import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { folioKeys } from '../../../../services/api/folio';
import { makeClient, mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { FolioSidebar } from '.';

const SPACES = [
  { key: 'ing', name: 'Ingeniería', kind: 'team', icon: null },
  { key: 'ai', name: 'AI Tools', kind: 'team', icon: '🤖' },
  { key: '~luis', name: 'Luis', kind: 'personal', icon: null },
];

function setup(role: 'admin' | 'creator' | 'reader', path = '/folio') {
  const folio = { handle: 'luis', display_name: 'Luis', kind: 'human', role };
  mockFetch({
    'GET /api/v1/folio/me': { status: 200, body: folio },
    'GET /api/v1/folio/spaces': { status: 200, body: { items: SPACES } },
    'GET /api/v1/folio/submissions': { status: 200, body: { items: [{ id: 's1' }] } },
    'GET /api/v1/folio/me/tasks': {
      status: 200,
      body: {
        items: [
          { id: 't1', bucket: 'today' },
          { id: 't2', bucket: 'upcoming' },
        ],
      },
    },
  });
  const client = makeClient();
  client.setQueryData(folioKeys.me, folio);
  renderWithProviders(<FolioSidebar open={false} onClose={() => {}} />, client, path);
}

describe('FolioSidebar', () => {
  it('has the suite switch first and the places you can go', async () => {
    setup('creator');
    const aside = await screen.findByRole('complementary');
    const first = within(aside).getAllByRole('button')[0];
    expect(first).toHaveAccessibleName(/Folio/);
    for (const name of ['Home', 'Search', 'For you', 'My tasks', 'Favorites']) {
      expect(screen.getByRole('link', { name: new RegExp(name) })).toBeInTheDocument();
    }
    expect(await screen.findByTitle('1 overdue or due today')).toHaveTextContent('1');
  });

  it('lists the team spaces and highlights the one you are in', async () => {
    setup('creator', '/folio/s/ing');
    const spaces = await screen.findByRole('navigation', { name: 'Spaces' });
    const links = await within(spaces).findAllByRole('link');
    expect(links.map((l) => l.textContent)).toEqual(['IIngeniería', '🤖AI Tools']);
    expect(links[1]).not.toHaveAttribute('aria-current');
    expect(links[0]).toHaveAttribute('aria-current', 'page');
    expect(within(spaces).getByRole('button', { name: 'New space' })).toBeInTheDocument();
  });

  it('shows admins approvals with the count and Folio admin', async () => {
    setup('admin');
    expect(await screen.findByTitle('1 waiting for approval')).toHaveTextContent('1');
    expect(screen.getByRole('link', { name: /Approvals/ })).toHaveAttribute(
      'href',
      '/folio/approvals',
    );
    expect(screen.getByRole('link', { name: 'Folio admin' })).toHaveAttribute(
      'href',
      '/folio/admin',
    );
  });

  it('hides approvals, admin and new space from readers', async () => {
    setup('reader');
    await screen.findByRole('link', { name: 'Ingeniería' });
    expect(screen.queryByRole('link', { name: /Approvals/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Folio admin' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'New space' })).not.toBeInTheDocument();
  });
});
