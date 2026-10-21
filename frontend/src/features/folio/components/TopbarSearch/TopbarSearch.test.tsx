import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { TopbarSearch } from '.';

const HIT = {
  node_id: 'n1',
  title: 'Connect an agent',
  description: '',
  section: ['Connect it'],
  anchor: 'connect-it',
  url: '/folio/p/n1-connect-an-agent#connect-it',
  snippet: 'Create the **agent**.',
  space: 'docs',
  doc_type: null,
  score: 1,
  matched_by: ['text'],
};

describe('TopbarSearch', () => {
  it('shows results while you type, after a short pause', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/search': { status: 200, body: { mode: 'hybrid', items: [HIT] } },
    });
    renderWithProviders(<TopbarSearch />);
    const box = await screen.findByRole('combobox', { name: 'Search the docs' });
    await userEvent.type(box, 'agen');
    const option = await screen.findByRole('option');
    expect(option).toHaveTextContent('Connect an agent');
    expect(screen.getByRole('link', { name: /Connect an agent/ })).toHaveAttribute(
      'href',
      '/folio/p/n1-connect-an-agent#connect-it',
    );
    // One request for the whole word, not one per key.
    expect(calls.filter((c) => c.path.startsWith('/api/v1/folio/search'))).toHaveLength(1);
    expect(calls[0]?.path).toContain('q=agen&mode=hybrid&limit=5');
  });

  it('picks a result with the arrows and closes with Escape', async () => {
    mockFetch({
      'GET /api/v1/folio/search': { status: 200, body: { mode: 'hybrid', items: [HIT] } },
    });
    renderWithProviders(<TopbarSearch />);
    const box = await screen.findByRole('combobox', { name: 'Search the docs' });
    await userEvent.type(box, 'agent');
    await screen.findByRole('option');
    await userEvent.keyboard('{ArrowDown}');
    expect(screen.getByRole('option')).toHaveAttribute('aria-selected', 'true');
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeInTheDocument());
  });

  it('says when nothing matches', async () => {
    mockFetch({
      'GET /api/v1/folio/search': { status: 200, body: { mode: 'hybrid', items: [] } },
    });
    renderWithProviders(<TopbarSearch />);
    await userEvent.type(await screen.findByRole('combobox'), 'zzz');
    expect(await screen.findByText('Nothing matches “zzz”.')).toBeInTheDocument();
  });
});
