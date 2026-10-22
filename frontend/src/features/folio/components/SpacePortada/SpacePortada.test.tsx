import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SpacePortada } from '.';

const doc = (id: string, title: string, description = '') => ({
  id,
  slug: id,
  title,
  kind: 'page',
  icon: null,
  space: 'eng',
  parent_id: null,
  version: 1,
  metadata: { description },
  published_at: '2026-10-20T12:00:00Z',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-21T12:00:00Z',
});

const OVERVIEW = {
  pages: 6,
  folders: 1,
  sections: [
    { key: 'specs', doc_types: ['build-spec'], visible: true, count: 2 },
    { key: 'decisions', doc_types: ['decision-log'], visible: false, count: 4 },
    { key: 'guides', doc_types: ['how-to'], visible: true, count: 3 },
    { key: 'docs', doc_types: ['reference'], visible: true, count: 0 },
  ],
  participants: [],
  everyone_role: 'reader',
};

function answer(q: string) {
  if (q.includes('start-here')) return [doc('g0', 'Onboarding', 'Empieza aquí.')];
  if (q.includes('build-spec')) return [doc('s5', 'Etapa 5', 'Integraciones')];
  if (q.includes('decision-log')) return [doc('a1', 'pgvector')];
  if (q.includes('how-to')) return [doc('g0', 'Onboarding'), doc('g1', 'Despliegue')];
  return [doc('g1', 'Despliegue')];
}

describe('SpacePortada', () => {
  it('starts with the pinned page and shows the latest of each visible section', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces/eng/overview': { status: 200, body: OVERVIEW },
      'GET /api/v1/folio/nodes': (req) => ({
        status: 200,
        body: { items: answer(new URL(req.url).searchParams.get('q') ?? '') },
      }),
    });
    renderWithProviders(<SpacePortada space="eng" />);
    expect(await screen.findByRole('link', { name: /Onboarding/ })).toHaveAttribute(
      'href',
      '/folio/p/g0-g0',
    );
    expect(await screen.findByRole('link', { name: /Etapa 5/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'See all 2' })).toHaveAttribute(
      'href',
      '/folio/s/eng/specs',
    );
    expect(screen.queryByText('pgvector')).not.toBeInTheDocument();
    expect(await screen.findAllByRole('link', { name: /Despliegue/ })).toHaveLength(2);
  });
});
