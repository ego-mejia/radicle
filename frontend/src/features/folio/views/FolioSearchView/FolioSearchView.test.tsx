import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { FolioSearchView } from '.';

const HIT = {
  node_id: 'n1',
  title: 'Connect an agent',
  description: 'How to connect an agent over MCP.',
  section: ['Setup', 'Connect it'],
  anchor: 'connect-it',
  url: '/folio/p/n1-connect-an-agent#connect-it',
  snippet: 'Create the **agent** in Admin.',
  space: 'docs',
  doc_type: 'how-to',
  score: 0.03,
  matched_by: ['text', 'semantic'],
};

const SCHEMA = {
  status: 200,
  body: {
    fields: [],
    doc_types: [{ key: 'how-to', name: 'How-to' }],
    audiences: [],
    languages: [{ key: 'es', name: 'Español' }],
  },
};

function stub(search: (r: Request) => { status: number; body: unknown }) {
  return mockFetch({
    'GET /api/v1/folio/spaces': { status: 200, body: { items: [{ key: 'docs', name: 'Docs' }] } },
    'GET /api/v1/folio/metadata-schema': SCHEMA,
    'GET /api/v1/folio/search': (r) => search(r),
  });
}

describe('FolioSearchView', () => {
  it('searches and shows each hit at its section', async () => {
    const calls = stub(() => ({ status: 200, body: { mode: 'hybrid', items: [HIT] } }));
    renderWithProviders(<FolioSearchView />);
    await userEvent.type(await screen.findByRole('searchbox'), 'agent');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    const link = await screen.findByRole('link', { name: 'Connect an agent' });
    expect(link).toHaveAttribute('href', '/folio/p/n1-connect-an-agent#connect-it');
    expect(screen.getByText('docs › Setup › Connect it')).toBeInTheDocument();
    expect(screen.getByText('agent', { selector: 'mark' })).toBeInTheDocument();
    expect(screen.getByText('words')).toBeInTheDocument();
    expect(screen.getByText('meaning')).toBeInTheDocument();
    expect(calls.find((c) => c.path.startsWith('/api/v1/folio/search'))?.path).toContain(
      'q=agent&mode=hybrid',
    );
  });

  it('filters and switches mode', async () => {
    const calls = stub(() => ({ status: 200, body: { mode: 'text', items: [] } }));
    renderWithProviders(<FolioSearchView />);
    await userEvent.type(await screen.findByRole('searchbox'), 'deploy');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByText('Nothing matches “deploy”.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Words' }));
    await screen.findByRole('option', { name: 'How-to' });
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Document type' }),
      'how-to',
    );
    await waitFor(() => expect(calls.at(-1)?.path).toMatch(/q=deploy&mode=text.*doc_type=how-to/));
  });

  it('explains when semantic search has no AI provider', async () => {
    stub(() => ({
      status: 422,
      body: { status: 422, detail: 'Semantic search needs an AI provider.', errors: [] },
    }));
    renderWithProviders(<FolioSearchView />);
    await userEvent.type(await screen.findByRole('searchbox'), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByText('Semantic search needs an AI provider.')).toBeInTheDocument();
  });
});
