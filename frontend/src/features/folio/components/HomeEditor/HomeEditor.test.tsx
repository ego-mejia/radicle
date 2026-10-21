import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { HomeDraft } from '../../../../services/api/folio';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { HomeEditor } from '.';

const DRAFT: HomeDraft = {
  layout: {
    columns: 12,
    blocks: [
      { id: 'featured', type: 'featured', x: 0, y: 0, w: 7, h: 4, config: { node: null } },
      { id: 'q', type: 'query', x: 7, y: 0, w: 5, h: 4, config: { title: 'Runbooks', rql: 'x' } },
    ],
  },
  saved: false,
  updated_at: null,
};

describe('HomeEditor', () => {
  it('adds a block, saves the draft and publishes it', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/admin/home/draft': { status: 200, body: DRAFT },
      'PUT /api/v1/folio/admin/home/draft': (_req, body) => ({
        status: 200,
        body: { layout: body, saved: true, updated_at: '2026-10-21T10:00:00Z' },
      }),
      'POST /api/v1/folio/admin/home/publish': { status: 201, body: {} },
    });
    renderWithProviders(<HomeEditor />);
    expect(await screen.findByText('Runbooks')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Publish' })).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Text' }));
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Remove Featured' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save draft' }));
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PUT')).toBe(true));
    const put = calls.find((c) => c.method === 'PUT')?.body as { blocks: { id: string }[] };
    expect(put.blocks.map((b) => b.id)).toEqual(['q', 'text']);
    expect(put.blocks[1]).toMatchObject({ type: 'text', x: 0, y: 4, w: 6, h: 2 });

    const publish = await screen.findByRole('button', { name: 'Publish' });
    await vi.waitFor(() => expect(publish).toBeEnabled());
    await userEvent.click(publish);
    await vi.waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/publish'))).toBe(true),
    );
  });

  it('marks the block a 422 complains about', async () => {
    mockFetch({
      'GET /api/v1/folio/admin/home/draft': { status: 200, body: DRAFT },
      'PUT /api/v1/folio/admin/home/draft': {
        status: 422,
        body: {
          status: 422,
          title: 'Unprocessable',
          detail: 'The layout has problems',
          errors: [{ field: 'blocks[1].config.rql', message: 'Unknown field x', position: 0 }],
        },
      },
    });
    renderWithProviders(<HomeEditor />);
    await userEvent.click(await screen.findByRole('button', { name: 'Search' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('q: Unknown field x');
  });
});
