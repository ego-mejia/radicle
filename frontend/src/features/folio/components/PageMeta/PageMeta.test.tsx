import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { PageMeta } from '.';

describe('PageMeta', () => {
  it('shows the owner, state and catalogs of the published version', async () => {
    const metadata = {
      owner: 'fernando',
      doc_type: 'how-to',
      language: 'es',
      labels: ['mcp', 'agentes'],
      audiences: ['everyone'],
    };
    renderWithProviders(<PageMeta metadata={metadata} status="verified" version={3} />);
    const card = await screen.findByRole('region', { name: 'About this page' });
    expect(within(card).getByText('@fernando')).toBeInTheDocument();
    expect(within(card).getByText('Verified')).toBeInTheDocument();
    expect(within(card).getByText('how-to')).toBeInTheDocument();
    expect(within(card).getByText('v3')).toBeInTheDocument();
    expect(within(card).getByText('everyone')).toBeInTheDocument();
    const labels = within(card).getByRole('list', { name: 'Labels' });
    expect(
      within(labels)
        .getAllByRole('listitem')
        .map((l) => l.textContent),
    ).toEqual(['#mcp', '#agentes']);
  });

  it('copes with a draft that has no metadata yet', async () => {
    renderWithProviders(<PageMeta metadata={null} status="draft" version={null} />);
    expect(await screen.findByText('Draft')).toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Labels' })).toBeNull();
  });
});
