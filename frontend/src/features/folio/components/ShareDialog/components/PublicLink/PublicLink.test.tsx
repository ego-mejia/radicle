import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { ShareDialog } from '../..';

const LIST = 'GET /api/v1/folio/public-links';
const link = {
  id: 'l1',
  url: 'http://localhost:8000/pub/tok',
  target_type: 'node',
  target_id: 'n1',
  noindex: true,
  view_count: 3,
  created_at: '2026-10-21T10:00:00Z',
};

async function open() {
  renderWithProviders(
    <ShareDialog nodeId="n1" title="Deploy" space="guias" open onOpenChange={() => {}} />,
  );
  fireEvent.click(await screen.findByRole('tab', { name: 'Public link' }));
}

describe('PublicLink', () => {
  it('creates a page link hidden from search engines by default', async () => {
    let created = false;
    const calls = mockFetch({
      [LIST]: () => ({ status: 200, body: { items: created ? [link] : [] } }),
      'POST /api/v1/folio/public-links': () => {
        created = true;
        return { status: 201, body: link };
      },
    });
    await open();
    const page = await screen.findByRole('group', { name: 'This page' });
    expect(within(page).getByLabelText('Hide from search engines')).toBeChecked();
    fireEvent.click(within(page).getByRole('button', { name: 'Create link' }));
    expect(await within(page).findByDisplayValue(link.url)).toBeVisible();
    expect(within(page).getByText(/Opened 3 times · hidden from search engines/)).toBeVisible();
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ node: 'n1', noindex: true });
  });

  it('revokes a link', async () => {
    let live = true;
    const calls = mockFetch({
      [LIST]: (request) => {
        const forPage = new URL(request.url).searchParams.has('node');
        return { status: 200, body: { items: live && forPage ? [link] : [] } };
      },
      'DELETE /api/v1/folio/public-links/l1': () => {
        live = false;
        // The API answers 204; a mocked Response can't carry a body with it.
        return { status: 200, body: {} };
      },
    });
    await open();
    const page = await screen.findByRole('group', { name: 'This page' });
    fireEvent.click(await within(page).findByRole('button', { name: 'Revoke' }));
    expect(await within(page).findByRole('button', { name: 'Create link' })).toBeVisible();
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true));
  });

  it('tells people who are not space admins', async () => {
    mockFetch({ [LIST]: { status: 403, body: { status: 403, detail: 'no', errors: [] } } });
    await open();
    await waitFor(() =>
      expect(screen.getAllByText("Only the space's admins create public links.")).toHaveLength(2),
    );
  });
});
