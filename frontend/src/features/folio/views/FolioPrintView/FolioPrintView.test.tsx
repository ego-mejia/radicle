import { QueryClientProvider } from '@tanstack/react-query';
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
} from '@tanstack/react-router';
import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ThemeModeProvider } from '../../../../contexts/ThemeModeContext';
import { makeClient, mockFetch } from '../../../../test/renderWithProviders';
import i18n from '../../../../i18n';
import { FolioPrintView, SETTLE_MS } from '.';
import { printLanguage } from './language';

const page = (id: string, title: string) => ({
  id,
  kind: 'page',
  title,
  slug: title.toLowerCase(),
  icon: null,
  parent_id: null,
  cover_asset_id: null,
  published_at: '2026-10-20T10:00:00Z',
  version: 1,
  metadata: {},
  content_json: {
    type: 'doc',
    content: [{ type: 'image', attrs: { assetId: `img-${id}`, alt: `Imagen ${title}` } }],
  },
  children: [],
});

function renderAt(path: string) {
  const root = createRootRoute();
  const route = createRoute({
    getParentRoute: () => root,
    path: '/print/$token',
    component: FolioPrintView,
  });
  const router = createRouter({
    routeTree: root.addChildren([route]),
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

afterEach(() => vi.useRealTimers());

describe('FolioPrintView', () => {
  it('lays out every page with its files and says when it is ready to print', async () => {
    mockFetch({
      'GET /api/v1/folio/print/tok': {
        status: 200,
        body: {
          space: { name: 'Guías', description: '', icon: null, cover_asset_id: null },
          pages: [page('a', 'Uno'), page('b', 'Dos')],
        },
      },
    });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { container } = renderAt('/print/tok');
    expect(await screen.findByRole('heading', { name: 'Dos' })).toBeVisible();
    expect(screen.getByAltText('Imagen Uno')).toHaveAttribute(
      'src',
      '/api/v1/folio/print/tok/assets/img-a',
    );
    expect(container.querySelector('[data-print-ready]')).toBeNull();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(SETTLE_MS + 10);
    });
    expect(container.querySelector('[data-print-ready]')).not.toBeNull();
  });

  it('prints in the language of the doc, not the browser', async () => {
    await i18n.changeLanguage('en');
    mockFetch({
      'GET /api/v1/folio/print/es': {
        status: 200,
        body: {
          space: { name: 'Guías', description: '', icon: null, cover_asset_id: null },
          pages: [{ ...page('a', 'Uno'), metadata: { language: 'es' } }],
        },
      },
    });
    renderAt('/print/es');
    expect(await screen.findByRole('heading', { name: 'Uno' })).toBeVisible();
    await vi.waitFor(() => expect(i18n.language).toBe('es'));
    await i18n.changeLanguage('en');
  });

  it('keeps the browser language when the doc names none it knows', () => {
    expect(printLanguage({ language: 'es-MX' })).toBe('es');
    expect(printLanguage({ language: 'fr' })).toBeNull();
    expect(printLanguage(undefined)).toBeNull();
  });
});
