import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SectionDocs } from '.';

const DOC = {
  id: 'n1',
  slug: 'despliegue',
  title: 'Guía de despliegue',
  kind: 'page',
  icon: null,
  space: 'eng',
  parent_id: null,
  version: 2,
  metadata: { description: 'De main a producción.', owner: '@luis' },
  published_at: '2026-10-20T12:00:00Z',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-20T12:00:00Z',
};

describe('SectionDocs', () => {
  it('lists the section with its RQL and links each page', async () => {
    const calls = mockFetch({ 'GET /api/v1/folio/nodes': { status: 200, body: { items: [DOC] } } });
    renderWithProviders(<SectionDocs space="eng" section="guides" />);
    const link = await screen.findByRole('link', { name: /Guía de despliegue/ });
    expect(link).toHaveAttribute('href', '/folio/p/n1-despliegue');
    expect(screen.getByText('De main a producción.')).toBeInTheDocument();
    const q = new URLSearchParams(calls[0]?.path.split('?')[1] ?? '').get('q');
    expect(q).toBe('space = eng AND doc_type in (how-to, guide) ORDER BY published DESC');
  });

  it('says when nothing matches', async () => {
    mockFetch({ 'GET /api/v1/folio/nodes': { status: 200, body: { items: [] } } });
    renderWithProviders(<SectionDocs space="eng" section="docs" q="vpn" />);
    expect(await screen.findByText(/No page title matches “vpn”/)).toBeInTheDocument();
  });
});
