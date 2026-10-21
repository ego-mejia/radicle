import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { makeClient, mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { EVERY_BLOCK } from '../../editor/everyBlock';
import { PageEditor } from '.';

const NODE = {
  id: '9f3c0000-0000-4000-8000-000000000001',
  kind: 'page',
  title: 'Conecta un agente',
  slug: 'conecta-un-agente',
  icon: null,
  space: 'docs',
  parent_id: null,
  cover_asset_id: null,
  published_at: null,
  created_at: '2026-10-20T10:00:00Z',
  updated_at: '2026-10-20T10:00:00Z',
  breadcrumbs: [],
  version: null,
  metadata: null,
  content_json: null,
};
const DRAFT = {
  content_json: EVERY_BLOCK,
  content_md: '',
  metadata: {},
  saved: true,
  updated_at: null,
};

describe('PageEditor', () => {
  it('opens the draft with every block and saves the title', async () => {
    const calls = mockFetch({
      [`GET /api/v1/folio/nodes/${NODE.id}`]: { status: 200, body: NODE },
      [`GET /api/v1/folio/nodes/${NODE.id}/draft`]: { status: 200, body: DRAFT },
      [`PATCH /api/v1/folio/nodes/${NODE.id}`]: (_r, body) => ({
        status: 200,
        body: { ...NODE, ...(body as object) },
      }),
    });
    renderWithProviders(<PageEditor nodeId={NODE.id} onPublish={() => undefined} />, makeClient());
    expect(await screen.findByText('Ojo con el token.')).toBeInTheDocument();
    expect(screen.getByText('@fernando')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Publish' })).toBeInTheDocument();

    const title = screen.getByRole('textbox', { name: 'Title' });
    await userEvent.clear(title);
    await userEvent.type(title, 'Guía MCP');
    await waitFor(
      () =>
        expect(calls.filter((c) => c.method === 'PATCH').at(-1)?.body).toEqual({
          title: 'Guía MCP',
          icon: null,
        }),
      { timeout: 3000 },
    );
    expect(await screen.findByText('Saved')).toBeInTheDocument();
  });
});
