import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { MyShortcuts } from '.';

const page = (id: string, title: string) => ({
  id,
  kind: 'page',
  title,
  slug: title.toLowerCase(),
  icon: null,
  status: 'published',
});

describe('MyShortcuts', () => {
  it('lists favorites and recent reads', async () => {
    mockFetch({
      'GET /api/v1/folio/me/recents': { status: 200, body: { items: [page('r1', 'Deploy')] } },
      'GET /api/v1/folio/me/favorites': {
        status: 200,
        body: { nodes: [page('f1', 'Guía')], spaces: [{ key: 'ops', name: 'Ops' }] },
      },
    });
    renderWithProviders(<MyShortcuts />);
    const favs = await screen.findByRole('region', { name: 'Favorites' });
    expect(within(favs).getByRole('link', { name: 'Ops' })).toHaveAttribute('href', '/folio/s/ops');
    expect(within(favs).getByRole('link', { name: 'Guía' })).toBeInTheDocument();
    const recents = screen.getByRole('region', { name: 'Recent' });
    expect(within(recents).getByRole('link', { name: 'Deploy' })).toHaveAttribute(
      'href',
      '/folio/p/r1-deploy',
    );
  });
});
