import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { makeClient, mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { PageEditor } from '../PageEditor';

const ID = '9f3c0000-0000-4000-8000-000000000001';
const NODE = {
  id: ID,
  kind: 'page',
  title: 'Guía MCP',
  slug: 'guia-mcp',
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
const DOC = {
  type: 'doc',
  content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Crea el agente.' }] }],
};
const DRAFT = { content_json: DOC, content_md: '', metadata: {}, saved: true, updated_at: null };

function page(available: boolean) {
  return {
    [`GET /api/v1/folio/nodes/${ID}`]: { status: 200, body: NODE },
    [`GET /api/v1/folio/nodes/${ID}/draft`]: { status: 200, body: DRAFT },
    [`PUT /api/v1/folio/nodes/${ID}/draft`]: { status: 200, body: DRAFT },
    'GET /api/v1/folio/ai/availability': {
      status: 200,
      body: available
        ? { available: true, reason: null, message: null }
        : { available: false, reason: 'no_provider', message: 'No provider' },
    },
    'POST /api/v1/folio/ai/summarize': {
      status: 200,
      body: { summary: '- Crea el agente.\n- Conéctalo por **MCP**.' },
    },
  };
}

describe('AiMenu', () => {
  it('summarizes in a side panel and inserts only when asked', async () => {
    const calls = mockFetch(page(true));
    renderWithProviders(<PageEditor nodeId={ID} />, makeClient());
    await userEvent.click(await screen.findByRole('button', { name: 'AI' }));
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Summarize the page' }));
    const panel = await screen.findByRole('complementary', { name: 'Summary' });
    expect(await screen.findByText('MCP')).toBeInTheDocument();
    expect(calls.find((c) => c.path.endsWith('/summarize'))?.body).toEqual({ node_id: ID });
    expect(panel).toBeInTheDocument();
    const body = () => within(document.querySelector<HTMLElement>('.ProseMirror')!);
    expect(body().queryByRole('heading', { name: 'Summary' })).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: 'Insert at the top' }));
    expect(screen.queryByRole('complementary')).toBeNull();
    expect(await body().findByRole('heading', { name: 'Summary' })).toBeInTheDocument();
    expect(body().getByText('Conéctalo por MCP.')).toBeInTheDocument();
  });

  it('is not there without a provider', async () => {
    const calls = mockFetch(page(false));
    renderWithProviders(<PageEditor nodeId={ID} />, makeClient());
    expect(await screen.findByText('Crea el agente.')).toBeInTheDocument();
    await waitFor(() => expect(calls.some((c) => c.path.includes('/ai/availability'))).toBe(true));
    expect(screen.queryByRole('button', { name: 'AI' })).toBeNull();
  });
});
