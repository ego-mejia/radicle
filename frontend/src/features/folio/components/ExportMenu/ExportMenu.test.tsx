import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { ExportMenu } from '.';

const row = (status: string, extra: object = {}) => ({
  id: 'e1',
  format: 'pdf',
  scope: 'node',
  node_id: 'n1',
  status,
  filename: status === 'done' ? 'guia.pdf' : null,
  stats: {},
  download_url: status === 'done' ? '/api/v1/folio/exports/e1/download' : null,
  created_at: '2026-10-21T10:00:00Z',
  finished_at: null,
  ...extra,
});

afterEach(() => vi.restoreAllMocks());

async function pick(name: string) {
  await userEvent.click(await screen.findByRole('button', { name: 'Export' }));
  await userEvent.click(await screen.findByRole('menuitem', { name: new RegExp(name) }));
}

describe('ExportMenu', () => {
  it('exports in the chosen format and downloads the file when it is ready', async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const calls = mockFetch({
      'POST /api/v1/folio/exports': { status: 202, body: row('queued') },
      'GET /api/v1/folio/exports/e1': { status: 200, body: row('done') },
    });
    renderWithProviders(<ExportMenu target={{ node: 'n1' }} />);
    await pick('PDF');
    expect(await screen.findByText('guia.pdf is ready.')).toBeVisible();
    expect(click).toHaveBeenCalledTimes(1);
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ node: 'n1', format: 'pdf' });
    expect(screen.getByRole('button', { name: 'Export' })).toBeEnabled();
  });

  it('says why an export failed', async () => {
    mockFetch({
      'POST /api/v1/folio/exports': { status: 202, body: row('queued') },
      'GET /api/v1/folio/exports/e1': {
        status: 200,
        body: row('failed', { stats: { error: 'The export stopped: no Chromium' } }),
      },
    });
    renderWithProviders(<ExportMenu target={{ space: 'guias' }} />);
    await pick('Word');
    expect(await screen.findByText('The export stopped: no Chromium')).toBeVisible();
  });

  it('shows the API error, e.g. without the export permission', async () => {
    mockFetch({
      'POST /api/v1/folio/exports': {
        status: 403,
        body: {
          status: 403,
          detail: 'Exporting from Guías needs its export permission.',
          errors: [],
        },
      },
    });
    renderWithProviders(<ExportMenu target={{ space: 'guias' }} />);
    await pick('Markdown');
    await waitFor(() => expect(screen.getByText(/needs its export permission/)).toBeVisible());
  });
});
