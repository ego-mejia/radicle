import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { FolioNode } from '../../../../services/api/folio';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { doc, p, t } from '../DocContent/testDoc';
import { LiveDocHistory } from '.';

const ID = '9f3c0000-0000-4000-8000-000000000007';
const node = { id: ID, kind: 'live_doc', title: 'Minuta', slug: 'minuta' } as FolioNode;
const base = `/api/v1/folio/nodes/${ID}/snapshots`;
const SNAPSHOTS = [
  { id: 's2', created_at: '2026-10-21T10:20:00Z', authors: ['ana', 'fernando'] },
  { id: 's1', created_at: '2026-10-21T10:10:00Z', authors: [] },
];
const content = (id: string, text: string) => ({
  ...SNAPSHOTS.find((s) => s.id === id),
  content_json: doc(p(t(text))),
  content_md: text,
});

describe('LiveDocHistory', () => {
  it('shows each snapshot with its authors and restores an older one', async () => {
    const calls = mockFetch({
      [`GET ${base}`]: { status: 200, body: { items: SNAPSHOTS, next_cursor: null } },
      [`GET ${base}/s2`]: { status: 200, body: content('s2', 'Texto de ahora') },
      [`GET ${base}/s1`]: { status: 200, body: content('s1', 'Texto de antes') },
      [`POST ${base}/s1/restore`]: {
        status: 201,
        body: { id: 's3', created_at: '2026-10-21T10:25:00Z', authors: ['luis'] },
      },
    });
    renderWithProviders(<LiveDocHistory node={node} />);
    // The newest one opens first, and it is the current text: nothing to restore.
    expect(await screen.findByText('Texto de ahora')).toBeInTheDocument();
    expect(screen.getByText('ana, fernando')).toBeInTheDocument();
    expect(screen.getByText('No changes')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Restore this snapshot' })).toBeNull();

    const older = screen.getAllByRole('button', { pressed: false })[0]!;
    await userEvent.click(older);
    expect(await screen.findByText('Texto de antes')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Restore this snapshot' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Restore it' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path === `${base}/s1/restore`)).toBe(true),
    );
    expect(await screen.findByText('The doc is back to that snapshot')).toBeInTheDocument();
  });

  it('explains when there are no snapshots yet', async () => {
    mockFetch({ [`GET ${base}`]: { status: 200, body: { items: [], next_cursor: null } } });
    renderWithProviders(<LiveDocHistory node={node} />);
    expect(await screen.findByText(/No snapshots yet/)).toBeInTheDocument();
  });

  it('shows what the API says when a restore fails', async () => {
    mockFetch({
      [`GET ${base}`]: { status: 200, body: { items: SNAPSHOTS, next_cursor: null } },
      [`GET ${base}/s1`]: { status: 200, body: content('s1', 'Texto de antes') },
      [`GET ${base}/s2`]: { status: 200, body: content('s2', 'Texto de ahora') },
      [`POST ${base}/s1/restore`]: {
        status: 403,
        body: { status: 403, title: 'Forbidden', detail: 'Only editors restore.', errors: [] },
      },
    });
    renderWithProviders(<LiveDocHistory node={node} />);
    await screen.findByText('Texto de ahora');
    await userEvent.click(screen.getAllByRole('button', { pressed: false })[0]!);
    await userEvent.click(await screen.findByRole('button', { name: 'Restore this snapshot' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Restore it' }));
    expect(await screen.findByText('Only editors restore.')).toBeInTheDocument();
  });
});
