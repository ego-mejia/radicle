import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { PluginsTab } from '.';

const COUNTDOWN = {
  key: 'radicle.countdown',
  name: 'Cuenta regresiva',
  version: '1.0.0',
  description: 'Días que faltan',
  author: 'Radicle',
  enabled: true,
  hooks: ['folio.register_blocks'],
  manifest: {},
  installed_at: '2026-10-21T10:00:00Z',
  updated_at: '2026-10-21T10:00:00Z',
};
const EXAMPLE = { key: 'radicle.countdown', name: 'Cuenta regresiva', description: 'Días' };

describe('PluginsTab', () => {
  it('installs the example and turns it off', async () => {
    let installed = false;
    const calls = mockFetch({
      'GET /api/v1/admin/plugins': () => ({
        status: 200,
        body: {
          items: installed ? [COUNTDOWN] : [],
          hooks: ['folio.register_blocks'],
          examples: [{ ...EXAMPLE, installed }],
        },
      }),
      'POST /api/v1/admin/plugins/examples/radicle.countdown': () => {
        installed = true;
        return { status: 201, body: COUNTDOWN };
      },
      'PATCH /api/v1/admin/plugins/radicle.countdown': {
        status: 200,
        body: { ...COUNTDOWN, enabled: false },
      },
    });
    renderWithProviders(<PluginsTab />);
    expect(await screen.findByText(/No plugins yet/)).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole('button', { name: 'Install' })[0]!);
    expect(await screen.findByText('Installed')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Turn off' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({ enabled: false }),
    );
  });

  it('installs from a manifest and says when it is not JSON or is refused', async () => {
    const calls = mockFetch({
      'GET /api/v1/admin/plugins': {
        status: 200,
        body: { items: [], hooks: [], examples: [] },
      },
      'POST /api/v1/admin/plugins': {
        status: 422,
        body: { status: 422, detail: 'Unknown hook docket.board.', errors: [] },
      },
    });
    renderWithProviders(<PluginsTab />);
    const box = await screen.findByLabelText('Manifest');
    await userEvent.type(box, 'nope');
    await userEvent.click(screen.getAllByRole('button', { name: 'Install' }).at(-1)!);
    expect(await screen.findByText(/isn't valid JSON/)).toBeInTheDocument();
    await userEvent.clear(box);
    await userEvent.type(box, '{{"key": "acme.x"}');
    await userEvent.click(screen.getAllByRole('button', { name: 'Install' }).at(-1)!);
    expect(await screen.findByText('Unknown hook docket.board.')).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ manifest: { key: 'acme.x' } });
  });
});
