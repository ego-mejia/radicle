import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { folioKeys } from '../../services/api/folio';
import { makeClient, mockFetch, renderWithProviders } from '../../test/renderWithProviders';
import { FolioPage } from '.';

function setup(role: 'admin' | 'creator' | 'reader') {
  const folio = { handle: 'luis', display_name: 'Luis', kind: 'human', role };
  mockFetch({
    'GET /api/v1/folio/me': { status: 200, body: folio },
    'GET /api/v1/folio/spaces': { status: 200, body: { items: [] } },
    'GET /api/v1/folio/submissions': { status: 200, body: { items: [] } },
    'GET /api/v1/folio/me/tasks': { status: 200, body: { items: [] } },
    'GET /api/v1/folio/chat/availability': { status: 200, body: { available: true } },
  });
  const client = makeClient();
  client.setQueryData(folioKeys.me, folio);
  renderWithProviders(<FolioPage />, client, '/folio');
}

describe('FolioPage', () => {
  it('puts the sidebar on the left, search and Write over the content, and Radi', async () => {
    setup('creator');
    const aside = await screen.findByRole('complementary');
    expect(within(aside).getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/folio');
    const bar = screen.getByRole('banner');
    expect(within(bar).getByPlaceholderText('Search the docs')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Ask Radi for help' })).toBeInTheDocument();
    expect(within(bar).getByRole('button', { name: /Write/ })).toBeInTheDocument();
    expect(
      within(bar).getByRole('button', { name: 'Open menu', hidden: true }),
    ).toBeInTheDocument();
  });

  it('has no Write for readers', async () => {
    setup('reader');
    const bar = await screen.findByRole('banner');
    await screen.findByRole('button', { name: 'Ask Radi for help' });
    expect(within(bar).queryByRole('button', { name: /Write/ })).not.toBeInTheDocument();
  });
});
