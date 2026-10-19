import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  createMemoryHistory,
  createRootRoute,
  createRouter,
  RouterProvider,
} from '@tanstack/react-router';
import { render } from '@testing-library/react';
import { ThemeModeProvider } from '../contexts/ThemeModeContext';
import { ToastProvider } from '../contexts/ToastProvider';
import { authKeys } from '../services/api/auth';
import type { Me } from '../services/api/types';

export const ME: Me = {
  handle: 'luis',
  display_name: 'Luis',
  kind: 'human',
  email: 'luis@example.com',
  is_instance_admin: false,
  is_active: true,
  created_at: '2026-10-18T10:00:00Z',
  projects: [{ key: 'PA', name: 'ProyectoA', role: 'member' }],
};

export function makeClient(me: Me | null = ME) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (me) client.setQueryData(authKeys.me, me);
  return client;
}

/** Providers plus a one-route memory router, so components with <Link> render. */
export function renderWithProviders(ui: React.ReactElement, client = makeClient()) {
  const router = createRouter({
    routeTree: createRootRoute({ component: () => ui }),
    history: createMemoryHistory({ initialEntries: ['/'] }),
  });
  return render(
    <QueryClientProvider client={client}>
      <ThemeModeProvider>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </ThemeModeProvider>
    </QueryClientProvider>,
  );
}

type Handler = (request: Request, body: unknown) => { status: number; body: unknown } | undefined;

/** Stub fetch with a list of handlers; unmatched requests return 404 problems. */
export function mockFetch(handlers: Record<string, Handler | { status: number; body: unknown }>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  const fetchMock = async (input: Request) => {
    const url = new URL(input.url);
    const text = input.method === 'GET' ? '' : await input.text();
    const body = text ? JSON.parse(text) : undefined;
    calls.push({ method: input.method, path: url.pathname + url.search, body });
    const handler = handlers[`${input.method} ${url.pathname}`];
    const result = typeof handler === 'function' ? handler(input, body) : handler;
    const response = result ?? {
      status: 404,
      body: { status: 404, detail: 'not mocked', errors: [] },
    };
    return new Response(JSON.stringify(response.body), {
      status: response.status,
      headers: {
        'Content-Type': response.status >= 400 ? 'application/problem+json' : 'application/json',
      },
    });
  };
  globalThis.fetch = fetchMock as typeof fetch;
  return calls;
}
