import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { FolioForYouView } from '.';

const ITEM = {
  id: 'n1',
  slug: 'etapa-5',
  title: 'Etapa 5',
  description: 'Integraciones',
  doc_type: 'build-spec',
  space_name: 'Ingeniería',
  author_name: 'Ana',
  reading_minutes: 4,
};

describe('FolioForYouView', () => {
  it('lists the feed with links to each page', async () => {
    mockFetch({ 'GET /api/v1/folio/me/feed': { status: 200, body: { items: [ITEM] } } });
    renderWithProviders(<FolioForYouView />);
    const link = await screen.findByRole('link', { name: /Etapa 5/ });
    expect(link).toHaveAttribute('href', '/folio/p/n1-etapa-5');
    expect(link).toHaveTextContent('build-spec · Ingeniería');
  });

  it('says how to fill it when empty', async () => {
    mockFetch({ 'GET /api/v1/folio/me/feed': { status: 200, body: { items: [] } } });
    renderWithProviders(<FolioForYouView />);
    expect(await screen.findByText(/Follow a space or a person/)).toBeInTheDocument();
  });
});
