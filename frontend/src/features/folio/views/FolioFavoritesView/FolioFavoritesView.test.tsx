import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { FolioFavoritesView } from '.';

describe('FolioFavoritesView', () => {
  it('shows starred spaces and pages, then recents', async () => {
    mockFetch({
      'GET /api/v1/folio/me/favorites': {
        status: 200,
        body: {
          spaces: [{ key: 'ing', name: 'Ingeniería' }],
          nodes: [{ id: 'n1', slug: 'deploy', title: 'Guía de despliegue', icon: null }],
        },
      },
      'GET /api/v1/folio/me/recents': {
        status: 200,
        body: { items: [{ id: 'n2', slug: 'adr', title: 'pgvector', icon: null }] },
      },
    });
    renderWithProviders(<FolioFavoritesView />);
    expect(await screen.findByRole('link', { name: /Ingeniería/ })).toHaveAttribute(
      'href',
      '/folio/s/ing',
    );
    expect(screen.getByRole('link', { name: 'Guía de despliegue' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'pgvector' })).toHaveAttribute(
      'href',
      '/folio/p/n2-adr',
    );
  });

  it('says how to star something when empty', async () => {
    mockFetch({
      'GET /api/v1/folio/me/favorites': { status: 200, body: { spaces: [], nodes: [] } },
      'GET /api/v1/folio/me/recents': { status: 200, body: { items: [] } },
    });
    renderWithProviders(<FolioFavoritesView />);
    expect(await screen.findByText(/Star a space or a page/)).toBeInTheDocument();
  });
});
