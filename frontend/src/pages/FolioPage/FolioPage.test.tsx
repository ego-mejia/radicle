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
  it('puts the sidebar on the left and search, Ask and Write over the content', async () => {
    setup('creator');
    const aside = await screen.findByRole('complementary');
    expect(within(aside).getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/folio');
    const bar = screen.getByRole('banner');
    expect(within(bar).getByPlaceholderText('Search the docs')).toBeInTheDocument();
    expect(await within(bar).findByRole('button', { name: /Ask/ })).toBeInTheDocument();
    expect(within(bar).getByRole('button', { name: /Write/ })).toBeInTheDocument();
    expect(
      within(bar).getByRole('button', { name: 'Open menu', hidden: true }),
    ).toBeInTheDocument();
  });

  it('has no Write for readers', async () => {
    setup('reader');
    const bar = await screen.findByRole('banner');
    await within(bar).findByRole('button', { name: /Ask/ });
    expect(within(bar).queryByRole('button', { name: /Write/ })).not.toBeInTheDocument();
  });
});
