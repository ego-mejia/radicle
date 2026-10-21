import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { RqlBar } from '.';

const DOC = {
  id: 'n1',
  kind: 'page',
  title: 'Deploy guide',
  slug: 'deploy-guide',
  space: 'ops',
  published_at: '2026-10-20T10:00:00Z',
  metadata: { doc_type: 'how-to' },
};

describe('RqlBar', () => {
  it('runs a query and lists the docs', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/nodes': { status: 200, body: { items: [DOC], next_cursor: null } },
    });
    renderWithProviders(<RqlBar rql="space = ops" onRun={() => {}} />);
    const link = await screen.findByRole('link', { name: 'Deploy guide' });
    expect(link).toHaveAttribute('href', '/folio/p/n1-deploy-guide');
    expect(screen.getByRole('cell', { name: 'how-to' })).toBeInTheDocument();
    expect(calls[0]?.path).toContain('q=space%20%3D%20ops');
  });

  it('sends what you type to run', async () => {
    mockFetch({});
    const onRun = vi.fn();
    renderWithProviders(<RqlBar rql="" onRun={onRun} />);
    await userEvent.type(await screen.findByRole('textbox', { name: 'RQL query' }), '#mcp ');
    await userEvent.click(screen.getByRole('button', { name: 'Run' }));
    expect(onRun).toHaveBeenCalledWith('#mcp');
  });

  it('points at the character an error is about', async () => {
    mockFetch({
      'GET /api/v1/folio/nodes': {
        status: 422,
        body: {
          status: 422,
          detail: "Unknown field 'spaec' at 0. Did you mean 'space'?",
          errors: [],
          position: 0,
        },
      },
    });
    renderWithProviders(<RqlBar rql="spaec = docs" onRun={() => {}} />);
    expect(await screen.findByRole('alert')).toHaveTextContent("Did you mean 'space'?");
    expect(screen.getByText(/spaec = docs\s+\^/)).toBeInTheDocument();
  });
});
