import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DocsSection } from '.';

const ref = (id: string, title: string, parent: string | null) => ({
  id,
  slug: id,
  title,
  kind: 'page',
  icon: null,
  space: 'eng',
  parent_id: parent,
  version: 1,
  metadata: { description: `Referencia de ${title}` },
  published_at: '2026-10-20T12:00:00Z',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-20T12:00:00Z',
});
const folder = (id: string, title: string) => ({
  id,
  kind: 'folder',
  title,
  slug: id,
  icon: null,
  status: 'draft',
  can_delete: true,
  children: [],
});

describe('DocsSection', () => {
  it('groups reference pages by their folder', async () => {
    mockFetch({
      'GET /api/v1/folio/nodes': {
        status: 200,
        body: {
          items: [ref('a', 'events', 'f1'), ref('b', 'search', 'f2'), ref('c', 'Glosario', null)],
        },
      },
      'GET /api/v1/folio/spaces/eng/tree': {
        status: 200,
        body: [folder('f1', 'Platform'), folder('f2', 'Folio')],
      },
    });
    renderWithProviders(<DocsSection space="eng" notice={<p>Aviso de Radi</p>} />);
    expect(await screen.findByRole('heading', { name: 'Platform' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Folio' })).toBeInTheDocument();
    const headings = screen.getAllByRole('heading').map((h) => h.textContent);
    expect(headings).toEqual(['Folio', 'Platform', 'General']);
    expect(screen.getByRole('link', { name: /events/ })).toHaveAttribute('href', '/folio/p/a-a');
    expect(screen.getByText('Aviso de Radi')).toBeInTheDocument();
  });
});
