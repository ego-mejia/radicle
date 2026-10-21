import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { folioKeys } from '../../../../services/api/folio';
import { makeClient, mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { PageHistory } from '.';

const ID = '9f3c0000-0000-4000-8000-000000000001';
const node = { id: ID, kind: 'page', title: 'Guía de MCP', slug: 'guia-de-mcp', version: 2 };
const version = (number: number, title: string) => ({
  number,
  title,
  change_note: number === 2 ? 'Agrego el token' : null,
  author: 'fernando',
  approved_by: number === 2 ? 'ana' : null,
  restored_from: null,
  created_at: '2026-10-20T10:00:00Z',
  metadata: {},
});
const diff = {
  from_version: 1,
  to_version: 2,
  title: { field: 'title', before: 'Guía', after: 'Guía de MCP' },
  metadata: [],
  blocks: [
    { op: 'added', block: { type: 'paragraph', content: [{ type: 'text', text: 'Token' }] } },
  ],
};

function setup(role = 'creator') {
  const folio = { handle: 'luis', display_name: 'Luis', kind: 'human', role };
  const calls = mockFetch({
    'GET /api/v1/folio/me': { status: 200, body: folio },
    [`GET /api/v1/folio/nodes/${ID}`]: { status: 200, body: node },
    [`GET /api/v1/folio/nodes/${ID}/versions`]: {
      status: 200,
      body: { items: [version(2, 'Guía de MCP'), version(1, 'Guía')] },
    },
    [`GET /api/v1/folio/nodes/${ID}/diff`]: { status: 200, body: diff },
    [`POST /api/v1/folio/nodes/${ID}/versions/1/restore`]: {
      status: 201,
      body: { ...version(3, 'Guía'), restored_from: 1 },
    },
  });
  const client = makeClient();
  client.setQueryData(folioKeys.me, folio);
  renderWithProviders(<PageHistory nodeId={ID} />, client);
  return calls;
}

describe('PageHistory', () => {
  it('lists the versions and shows the diff of the last two', async () => {
    const calls = setup();
    expect(await screen.findByText('Agrego el token')).toBeInTheDocument();
    expect(screen.getByText(/approved by ana/i)).toBeInTheDocument();
    expect(await screen.findByLabelText('Added')).toHaveTextContent('Token');
    expect(calls.some((c) => c.path.endsWith('/diff?from=1&to=2'))).toBe(true);
  });

  it('restores an old version after confirming', async () => {
    const calls = setup();
    await userEvent.click(await screen.findByRole('button', { name: 'Restore v1' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Restore it' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/1/restore'))).toBe(true),
    );
  });

  it('hides restore from readers', async () => {
    setup('reader');
    expect(await screen.findByText('Agrego el token')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Restore v1' })).not.toBeInTheDocument();
  });
});
