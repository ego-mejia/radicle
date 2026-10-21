import { QueryClientProvider } from '@tanstack/react-query';
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
} from '@tanstack/react-router';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ThemeModeProvider } from '../../../../contexts/ThemeModeContext';
import { makeClient, mockFetch } from '../../../../test/renderWithProviders';
import { FolioPublicView } from '.';

const TOKEN = 'abc123';
const PAGE = '11111111-1111-4111-8111-111111111111';
const node = (id: string, title: string, kind = 'page', parent_id: string | null = null) => ({
  id,
  kind,
  title,
  slug: title.toLowerCase(),
  icon: null,
  parent_id,
});
const page = {
  ...node(PAGE, 'Conectar un agente'),
  cover_asset_id: null,
  published_at: '2026-10-20T10:00:00Z',
  version: 2,
  metadata: { description: 'Paso a paso.', doc_type: 'how-to' },
  content_json: {
    type: 'doc',
    content: [
      { type: 'paragraph', content: [{ type: 'text', text: 'Pide el token.' }] },
      { type: 'image', attrs: { assetId: 'a1', alt: 'Diagrama' } },
      { type: 'ticketTable', attrs: { rql: 'project = PA' } },
    ],
  },
  children: [],
};
const space = {
  name: 'Guías',
  description: 'Todo para empezar.',
  icon: null,
  cover_asset_id: null,
};

function renderAt(path: string) {
  const root = createRootRoute();
  const routes = [
    createRoute({ getParentRoute: () => root, path: '/pub/$token', component: FolioPublicView }),
    createRoute({
      getParentRoute: () => root,
      path: '/pub/$token/$page',
      component: FolioPublicView,
    }),
  ];
  const router = createRouter({
    routeTree: root.addChildren(routes),
    history: createMemoryHistory({ initialEntries: [path] }),
  });
  return render(
    <QueryClientProvider client={makeClient(null)}>
      <ThemeModeProvider>
        <RouterProvider router={router} />
      </ThemeModeProvider>
    </QueryClientProvider>,
  );
}

describe('FolioPublicView', () => {
  it('shows a shared page with public assets and notes for live blocks', async () => {
    mockFetch({
      [`GET /api/v1/folio/pub/${TOKEN}`]: {
        status: 200,
        body: { target_type: 'node', space, nodes: [node(PAGE, 'Conectar un agente')], page },
      },
    });
    renderAt(`/pub/${TOKEN}`);
    expect(await screen.findByRole('heading', { name: 'Conectar un agente' })).toBeVisible();
    expect(screen.getByText('Paso a paso.')).toBeVisible();
    expect(screen.getByAltText('Diagrama')).toHaveAttribute(
      'src',
      `/api/v1/folio/pub/${TOKEN}/assets/a1`,
    );
    expect(screen.getByRole('note')).toHaveTextContent(/open it in Radicle/);
    expect(screen.queryByRole('navigation', { name: 'Pages' })).toBeNull();
  });

  it('lists a shared space and opens one of its pages', async () => {
    const folder = '22222222-2222-4222-8222-222222222222';
    const nodes = [
      node(folder, 'Inicio', 'folder'),
      node(PAGE, 'Conectar un agente', 'page', folder),
    ];
    mockFetch({
      [`GET /api/v1/folio/pub/${TOKEN}/pages/${PAGE}`]: {
        status: 200,
        body: { target_type: 'space', space, nodes, page },
      },
    });
    renderAt(`/pub/${TOKEN}/${PAGE}-conectar`);
    const nav = await screen.findByRole('navigation', { name: 'Pages' });
    expect(nav).toHaveTextContent('Inicio');
    expect(screen.getByRole('link', { name: 'Conectar un agente' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('says so when the link was revoked', async () => {
    mockFetch({});
    renderAt(`/pub/${TOKEN}`);
    expect(await screen.findByText("This link doesn't work")).toBeVisible();
  });
});
