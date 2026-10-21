import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { MilestoneDocs } from '.';

const doc = (id: string, title: string) => ({
  node: { id, title, slug: 'guia', kind: 'page' },
  space: 'eng',
  kind: null,
  anchor: null,
  url: `/folio/p/${id}-guia`,
  description: 'Cómo conectar un agente.',
});

describe('MilestoneDocs', () => {
  it("lists the milestone's docs", async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/links': { status: 200, body: { items: [doc('n1', 'Guía V1')] } },
    });
    renderWithProviders(<MilestoneDocs project="PA" milestone="V1" />);
    const link = await screen.findByRole('link', { name: 'Guía V1' });
    expect(link).toHaveAttribute('href', '/folio/p/n1-guia');
    expect(screen.getByRole('region', { name: 'Docs of V1' })).toHaveTextContent('1 doc');
    expect(calls[0]?.path).toBe('/api/v1/folio/links?milestone=PA%3AV1');
  });

  it('stays hidden without Folio access', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/links': { status: 403, body: { status: 403, detail: 'No', errors: [] } },
    });
    renderWithProviders(<MilestoneDocs project="PA" milestone="V1" />);
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(screen.queryByRole('region')).toBeNull();
  });
});
