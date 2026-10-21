import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { CommentReactions } from '.';

describe('CommentReactions', () => {
  it('shows what was used plus 👍, and reacts', async () => {
    mockFetch({
      'GET /api/v1/folio/reactions/comment/c1': {
        status: 200,
        body: [{ emoji: '🎉', count: 2, mine: false }],
      },
      [`PUT /api/v1/folio/reactions/comment/c1/${encodeURIComponent('👍')}`]: {
        status: 200,
        body: [
          { emoji: '👍', count: 1, mine: true },
          { emoji: '🎉', count: 2, mine: false },
        ],
      },
    });
    renderWithProviders(<CommentReactions commentId="c1" />);
    expect(await screen.findByRole('button', { name: /🎉.*2/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /🚀/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: /👍.*0/ }));
    expect(await screen.findByRole('button', { name: /👍.*1/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });
});
