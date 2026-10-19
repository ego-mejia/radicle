import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { renderWithProviders } from '../../test/renderWithProviders';
import { StatusPage } from '.';

function mockApi(responses: Record<string, { status: number; body: unknown }>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: Request) => {
      const { pathname } = new URL(input.url);
      const match = responses[pathname] ?? { status: 404, body: {} };
      return new Response(JSON.stringify(match.body), {
        status: match.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }),
  );
}

describe('StatusPage', () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage('en');
  });
  afterEach(() => vi.unstubAllGlobals());

  it('shows a healthy server that still needs setup', async () => {
    mockApi({
      '/api/v1/health': { status: 200, body: { status: 'ok', database: 'ok' } },
      '/api/v1/setup/status': { status: 200, body: { needs_setup: true } },
    });
    renderWithProviders(<StatusPage />);
    expect(await screen.findByText('Server and database are healthy.')).toBeInTheDocument();
    expect(await screen.findByText(/No admin yet/)).toBeInTheDocument();
  });

  it('shows an error when the server is down', async () => {
    mockApi({ '/api/v1/health': { status: 503, body: { detail: 'Database is unreachable.' } } });
    renderWithProviders(<StatusPage />);
    expect(await screen.findByText('The server is not reachable.')).toBeInTheDocument();
  });

  it('switches language to Spanish', async () => {
    mockApi({ '/api/v1/health': { status: 200, body: { status: 'ok', database: 'ok' } } });
    renderWithProviders(<StatusPage />);
    await userEvent.selectOptions(screen.getByLabelText('Language'), 'es');
    await waitFor(() => expect(screen.getByText('Radicle está corriendo')).toBeInTheDocument());
  });

  it('remembers an explicit theme choice', async () => {
    mockApi({ '/api/v1/health': { status: 200, body: { status: 'ok', database: 'ok' } } });
    renderWithProviders(<StatusPage />);
    await userEvent.selectOptions(screen.getByLabelText('Theme'), 'dark');
    expect(localStorage.getItem('radicle.theme')).toBe('dark');
    await userEvent.selectOptions(screen.getByLabelText('Theme'), 'system');
    expect(localStorage.getItem('radicle.theme')).toBeNull();
  });
});
