import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DocsPanel } from '.';

const NODE = '11111111-1111-1111-1111-111111111111';
const ref = { id: NODE, kind: 'page', title: 'Guía de agentes', slug: 'guia', icon: null };

describe('DocsPanel', () => {
  it('lists the docs that link to the ticket, at their section', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/links': {
        status: 200,
        body: {
          items: [
            {
              node: { ...ref, status: 'published' },
              space: 'eng',
              kind: 'created_from_text',
              anchor: 'conecta-un-agente',
              url: `/folio/p/${NODE}-guia#conecta-un-agente`,
            },
          ],
        },
      },
    });
    renderWithProviders(<DocsPanel ticketKey="PA-4" />);
    const link = await screen.findByRole('link', { name: /Guía de agentes/ });
    expect(link).toHaveAttribute('href', `/folio/p/${NODE}-guia#conecta-un-agente`);
    expect(screen.getByText('eng · created it')).toBeVisible();
    expect(calls[0]?.path).toBe('/api/v1/folio/links?ticket=PA-4');
  });

  it('says so when no doc links it, and hides without access to Folio', async () => {
    mockFetch({ 'GET /api/v1/folio/links': { status: 200, body: { items: [] } } });
    const { unmount } = renderWithProviders(<DocsPanel ticketKey="PA-4" />);
    expect(await screen.findByText('No Folio docs link to this ticket.')).toBeVisible();
    unmount();
    const calls = mockFetch({
      'GET /api/v1/folio/links': { status: 403, body: { status: 403, detail: 'no', errors: [] } },
    });
    renderWithProviders(<DocsPanel ticketKey="PA-5" />);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(screen.queryByRole('heading', { name: 'Docs' })).toBeNull();
  });
});
