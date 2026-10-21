import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { b, doc, p, t } from '../DocContent/testDoc';
import { ReadPage } from '.';

const CONTENT = doc(
  b('heading', { level: 1 }, t('Antes de empezar')),
  p(t('Necesitas ser admin.')),
  b('childPages', {}),
);
const META = {
  description: 'Cómo conectar un agente por MCP.',
  doc_type: 'how-to',
  owner: 'fernando',
  labels: ['mcp'],
  audiences: ['everyone'],
  language: 'es',
};
const NODE = {
  id: 'n1',
  kind: 'page',
  title: 'Conecta un agente',
  slug: 'conecta-un-agente',
  icon: null,
  space: 'docs',
  parent_id: null,
  cover_asset_id: null,
  published_at: '2026-10-20T10:00:00Z',
  created_at: '2026-10-19T10:00:00Z',
  updated_at: '2026-10-20T10:00:00Z',
  breadcrumbs: [{ id: 'f1', kind: 'folder', title: 'Guías', slug: 'guias', icon: null }],
  version: 2,
  status: 'verified',
  verified_until: null,
  can_edit: true,
  can_delete: true,
  archived_at: null,
  metadata: META,
  content_json: CONTENT,
};
const SPACE = { key: 'docs', name: 'Ingeniería', permissions: ['view', 'create'] };
const TREE = [
  {
    id: 'n1',
    kind: 'page',
    title: 'Conecta un agente',
    slug: 'conecta-un-agente',
    icon: null,
    children: [
      { id: 'c1', kind: 'page', title: 'Tokens', slug: 'tokens', icon: null, children: [] },
    ],
  },
];

function api(node: object = NODE, space: object = SPACE) {
  return mockFetch({
    'GET /api/v1/folio/nodes/n1': { status: 200, body: node },
    'GET /api/v1/folio/spaces/docs': { status: 200, body: space },
    'GET /api/v1/folio/spaces/docs/tree': { status: 200, body: TREE },
    'GET /api/v1/folio/nodes/n1/versions': {
      status: 200,
      body: { items: [{ number: 2, author: 'agente-docs' }] },
    },
    'GET /api/v1/folio/nodes/n1/comments': { status: 200, body: { items: [] } },
    'GET /api/v1/folio/people': { status: 200, body: { items: [] } },
    'GET /api/v1/folio/nodes/n1/draft': {
      status: 200,
      body: { content_json: CONTENT, content_md: '', metadata: {}, saved: true, updated_at: null },
    },
  });
}

describe('ReadPage', () => {
  beforeEach(() => localStorage.clear());

  it('counts the read, and shows analytics to space admins only', async () => {
    const calls = api();
    const { unmount } = renderWithProviders(<ReadPage nodeId="n1" />);
    await screen.findByRole('button', { name: 'Comments' });
    expect(screen.queryByRole('button', { name: 'Analytics' })).toBeNull();
    expect(calls.find((c) => c.path === '/api/v1/folio/analytics/views')?.body).toEqual({
      node_id: 'n1',
    });
    unmount();

    api(NODE, { ...SPACE, permissions: ['view', 'admin'] });
    renderWithProviders(<ReadPage nodeId="n1" />);
    expect(await screen.findByRole('button', { name: 'Analytics' })).toBeInTheDocument();
  });

  it('opens the comments beside the page', async () => {
    api();
    renderWithProviders(<ReadPage nodeId="n1" />);
    const toggle = await screen.findByRole('button', { name: 'Comments' });
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('No open comments.')).toBeInTheDocument();
  });

  it('switches to focus mode and remembers it for the reader', async () => {
    api();
    const { unmount } = renderWithProviders(<ReadPage nodeId="n1" />);
    await userEvent.click(await screen.findByRole('button', { name: 'Focus mode' }));
    expect(screen.getByRole('progressbar', { name: 'Reading progress' })).toBeInTheDocument();
    expect(screen.getByText('how-to · Ingeniería')).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Path' })).toBeNull();
    unmount();

    renderWithProviders(<ReadPage nodeId="n1" />);
    await userEvent.click(await screen.findByRole('button', { name: 'Exit focus' }));
    expect(screen.getByRole('navigation', { name: 'Path' })).toBeInTheDocument();
  });

  it('reads a published page like a magazine', async () => {
    api();
    renderWithProviders(<ReadPage nodeId="n1" />);
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Conecta un agente' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Cómo conectar un agente por MCP.')).toBeInTheDocument();
    expect(screen.getAllByText('@fernando')).toHaveLength(2); // byline and metadata
    expect(await screen.findByText(/published by @agente-docs/)).toBeInTheDocument();
    const path = screen.getByRole('navigation', { name: 'Path' });
    expect(await within(path).findByRole('link', { name: 'Ingeniería' })).toHaveAttribute(
      'href',
      '/folio/s/docs',
    );
    expect(within(path).getByRole('link', { name: 'Guías' })).toBeInTheDocument();
    const toc = screen.getByRole('navigation', { name: 'On this page' });
    expect(within(toc).getByRole('link', { name: 'Antes de empezar' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Tokens' })).toHaveAttribute(
      'href',
      '/folio/p/c1-tokens',
    );
    expect(screen.getByRole('link', { name: 'Edit' })).toHaveAttribute(
      'href',
      '/folio/p/n1-conecta-un-agente/edit',
    );
    expect(screen.getByRole('link', { name: 'History' })).toBeInTheDocument();
    expect(screen.getByText('Verified')).toBeInTheDocument();
  });

  it('hides editing from readers', async () => {
    api({ ...NODE, can_edit: false, can_delete: false }, { ...SPACE, permissions: ['view'] });
    renderWithProviders(<ReadPage nodeId="n1" />);
    expect(await screen.findByText('Necesitas ser admin.')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Edit' })).toBeNull();
  });

  it('shows the draft of a page that was never published', async () => {
    api({
      ...NODE,
      version: null,
      published_at: null,
      status: 'draft',
      content_json: null,
      metadata: null,
    });
    renderWithProviders(<ReadPage nodeId="n1" />);
    expect(await screen.findByRole('note')).toHaveTextContent('you are reading the draft');
    expect(screen.getByText('Necesitas ser admin.')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'History' })).toBeNull();
  });

  it('shows a live doc as it is now to those who cannot write in it', async () => {
    api(
      { ...NODE, kind: 'live_doc', version: null, status: 'draft', can_edit: false },
      { ...SPACE, permissions: ['view'] },
    );
    renderWithProviders(<ReadPage nodeId="n1" />);
    expect(await screen.findByText('Necesitas ser admin.')).toBeInTheDocument();
    expect(screen.queryByRole('note')).toBeNull();
  });

  it('explains a page it cannot open', async () => {
    mockFetch({});
    renderWithProviders(<ReadPage nodeId="n1" />);
    expect(await screen.findByText('This page is not available')).toBeInTheDocument();
  });
});
