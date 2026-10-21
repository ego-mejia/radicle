import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DocContent } from '../DocContent';
import { b, doc } from '../DocContent/testDoc';

const PAGE = {
  id: '11111111-1111-1111-1111-111111111111',
  title: 'Bienvenida',
  slug: 'bienvenida',
  kind: 'page',
  space: 'docs',
  published_at: '2026-10-20T10:00:00Z',
};

describe('PageList', () => {
  it("lists the label's pages as the server resolves them for the reader", async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/page-list': { status: 200, body: { items: [PAGE] } },
    });
    const block = b('pageList', { label: 'onboarding', limit: 5, order: 'title' });
    renderWithProviders(<DocContent doc={doc(block)} />);
    const link = await screen.findByRole('link', { name: 'Bienvenida' });
    expect(link).toHaveAttribute('href', `/folio/p/${PAGE.id}-bienvenida`);
    expect(screen.getByRole('navigation', { name: 'Pages labeled onboarding' })).toBeVisible();
    expect(calls[0]?.path).toBe('/api/v1/folio/page-list?label=onboarding&limit=5&order=title');
  });

  it('says so when no page it may see has the label', async () => {
    mockFetch({ 'GET /api/v1/folio/page-list': { status: 200, body: { items: [] } } });
    renderWithProviders(<DocContent doc={doc(b('pageList', { label: 'secreto' }))} />);
    expect(await screen.findByText(/No published pages you can see/)).toBeInTheDocument();
  });
});
