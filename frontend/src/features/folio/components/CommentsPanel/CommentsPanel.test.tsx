import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { CommentsPanel } from '.';

const comment = (id: string, body: string, mine = false) => ({
  id,
  thread_id: 't1',
  author: mine ? 'fernando' : 'ana',
  author_name: mine ? 'Fernando' : 'Ana',
  body_md: body,
  created_at: '2026-10-21T10:00:00Z',
  edited_at: null,
  mine,
});

const THREADS = [
  {
    id: 't1',
    kind: 'inline',
    anchor: { quote: 'conéctalo por MCP', prefix: '', suffix: '', offset: 0 },
    orphaned: false,
    resolved_at: null,
    resolved_by: null,
    comments: [comment('c1', '¿Y el token?'), comment('c2', 'Ya está @ana', true)],
  },
  {
    id: 't2',
    kind: 'inline',
    anchor: { quote: 'texto borrado', prefix: '', suffix: '', offset: 0 },
    orphaned: true,
    resolved_at: null,
    resolved_by: null,
    comments: [{ ...comment('c3', 'Huérfano'), thread_id: 't2' }],
  },
  {
    id: 't3',
    kind: 'footer',
    anchor: null,
    orphaned: false,
    resolved_at: '2026-10-21T11:00:00Z',
    resolved_by: 'luis',
    comments: [{ ...comment('c4', 'Listo'), thread_id: 't3' }],
  },
];

function api() {
  return mockFetch({
    'GET /api/v1/folio/nodes/n1/comments': { status: 200, body: { items: THREADS } },
    'GET /api/v1/folio/people': { status: 200, body: { items: [] } },
    'GET /api/v1/folio/reactions/comment/c1': { status: 200, body: [] },
    'GET /api/v1/folio/reactions/comment/c2': { status: 200, body: [] },
    'GET /api/v1/folio/reactions/comment/c3': { status: 200, body: [] },
    'GET /api/v1/folio/reactions/comment/c4': { status: 200, body: [] },
    'POST /api/v1/folio/comments/t1/resolve': { status: 200, body: THREADS[0] },
    'DELETE /api/v1/folio/comments/c2': { status: 204, body: null },
  });
}

describe('CommentsPanel', () => {
  it('filters open, orphaned and resolved threads', async () => {
    api();
    renderWithProviders(<CommentsPanel nodeId="n1" canComment />);
    expect(await screen.findByText('“conéctalo por MCP”')).toBeInTheDocument();
    expect(screen.queryByText('Huérfano')).toBeNull();
    expect(screen.getByRole('tab', { name: /Open 1/ })).toHaveAttribute('aria-selected', 'true');

    await userEvent.click(screen.getByRole('tab', { name: /Orphaned 1/ }));
    expect(await screen.findByText('The text it quoted was deleted')).toBeInTheDocument();
    expect(screen.getByText('Huérfano')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('tab', { name: /Resolved 1/ }));
    expect(await screen.findByText('Resolved by @luis')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Reopen/ })).toBeInTheDocument();
  });

  it('resolves a thread and deletes your own comment', async () => {
    const calls = api();
    renderWithProviders(<CommentsPanel nodeId="n1" canComment />);
    await userEvent.click(await screen.findByRole('button', { name: /Resolve/ }));
    await waitFor(() => expect(calls.some((c) => c.path.endsWith('/t1/resolve'))).toBe(true));
    expect(screen.getAllByRole('button', { name: 'Delete comment' })).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: 'Delete comment' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true));
  });

  it('readers without the comment permission only read', async () => {
    api();
    renderWithProviders(<CommentsPanel nodeId="n1" canComment={false} />);
    expect(await screen.findByText('¿Y el token?')).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'New comment' })).toBeNull();
    expect(screen.queryByRole('button', { name: /Resolve/ })).toBeNull();
  });
});
