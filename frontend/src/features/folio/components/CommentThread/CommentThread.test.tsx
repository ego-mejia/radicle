import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { CommentThread } from '.';

const THREAD = {
  id: 't1',
  kind: 'footer' as const,
  anchor: null,
  orphaned: false,
  resolved_at: null,
  resolved_by: null,
  comments: [
    {
      id: 'c1',
      thread_id: 't1',
      author: 'fernando',
      author_name: 'Fernando',
      body_md: 'Revisa **esto**',
      created_at: '2026-10-21T10:00:00Z',
      edited_at: null,
      mine: true,
    },
  ],
};

function setup() {
  mockFetch({
    'GET /api/v1/folio/reactions/comment/c1': {
      status: 200,
      body: [{ emoji: '🎉', count: 2, mine: false }],
    },
  });
  const props = {
    thread: THREAD,
    mentions: [{ handle: 'ana', name: 'Ana' }],
    canComment: true,
    onReply: vi.fn(async () => undefined),
    onEdit: vi.fn(async () => undefined),
    onDelete: vi.fn(),
    onResolve: vi.fn(),
  };
  renderWithProviders(<CommentThread {...props} />);
  return props;
}

describe('CommentThread', () => {
  it('shows the comment in Markdown with its reactions', async () => {
    setup();
    expect((await screen.findByText('esto')).tagName).toBe('STRONG');
    expect(await screen.findByRole('button', { name: /🎉.*2/ })).toBeInTheDocument();
  });

  it('replies and resolves', async () => {
    const props = setup();
    // Typing into CodeMirror isn't reliable under jsdom; the E2E types replies in Chrome.
    expect(await screen.findByRole('textbox', { name: 'Reply' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reply' })).toBeDisabled();
    expect(props.onReply).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: /Resolve/ }));
    expect(props.onResolve).toHaveBeenCalledWith(true);
  });

  it('edits your own comment', async () => {
    const props = setup();
    await userEvent.click(await screen.findByRole('button', { name: 'Edit comment' }));
    // The editor opens with the comment's Markdown (typing into a filled CodeMirror needs
    // layout jsdom doesn't have).
    expect(await screen.findByRole('textbox', { name: 'Edit comment' })).toHaveTextContent(
      'Revisa **esto**',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(props.onEdit).toHaveBeenCalledWith('c1', 'Revisa **esto**'));
  });
});
