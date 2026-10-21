import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { PageSocial } from '.';

function api() {
  return mockFetch({
    'GET /api/v1/folio/reactions/node/n1': {
      status: 200,
      body: [{ emoji: '👍', count: 2, mine: false }],
    },
    'GET /api/v1/folio/watch/node/n1': { status: 200, body: { watching: true } },
    'GET /api/v1/folio/me/favorites': { status: 200, body: { nodes: [], spaces: [] } },
    [`PUT /api/v1/folio/reactions/node/n1/${encodeURIComponent('👍')}`]: {
      status: 200,
      body: [{ emoji: '👍', count: 3, mine: true }],
    },
    'DELETE /api/v1/folio/watch/node/n1': { status: 200, body: null },
    'PUT /api/v1/folio/favorites/node/n1': { status: 200, body: null },
  });
}

describe('PageSocial', () => {
  it('reacts, unfollows and stars the page', async () => {
    const calls = api();
    renderWithProviders(<PageSocial nodeId="n1" />);
    const thumbs = await screen.findByRole('button', { name: /👍.*2/ });
    await userEvent.click(thumbs);
    expect(await screen.findByRole('button', { name: /👍.*3/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Unfollow' }));
    expect(await screen.findByRole('button', { name: 'Follow' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Add to favorites' }));
    expect(calls.some((c) => c.method === 'PUT' && c.path.endsWith('/favorites/node/n1'))).toBe(
      true,
    );
  });
});
