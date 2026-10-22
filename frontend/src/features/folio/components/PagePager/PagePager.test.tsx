import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { PagePager } from '.';

const page = (id: string, title: string) => ({
  id,
  slug: id,
  title,
  kind: 'page',
  icon: null,
  status: 'published',
  can_delete: false,
  children: [],
});
const TREE = [
  page('home', 'Inicio'),
  {
    ...page('specs', 'Specs'),
    kind: 'folder',
    children: [page('e3', 'Etapa 3'), page('e4', 'Etapa 4'), page('e5', 'Etapa 5')],
  },
];

describe('PagePager', () => {
  it('links the previous and next pages in the same folder', async () => {
    mockFetch({ 'GET /api/v1/folio/spaces/ing/tree': { status: 200, body: TREE } });
    renderWithProviders(<PagePager space="ing" nodeId="e4" />);
    expect(await screen.findByRole('link', { name: /Previous Etapa 3/ })).toHaveAttribute(
      'href',
      '/folio/p/e3-e3',
    );
    expect(screen.getByRole('link', { name: /Next Etapa 5/ })).toHaveAttribute(
      'href',
      '/folio/p/e5-e5',
    );
  });

  it('shows only the side that exists', async () => {
    mockFetch({ 'GET /api/v1/folio/spaces/ing/tree': { status: 200, body: TREE } });
    renderWithProviders(<PagePager space="ing" nodeId="e3" />);
    expect(await screen.findByRole('link', { name: /Next Etapa 4/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Previous/ })).not.toBeInTheDocument();
  });
});
