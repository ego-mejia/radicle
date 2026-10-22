import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { StaleDocsNotice } from '.';

const doc = (id: string, title: string) => ({
  id,
  slug: id,
  title,
  kind: 'page',
  icon: null,
  space: 'eng',
  parent_id: null,
  version: 2,
  metadata: {},
  published_at: '2026-08-01T12:00:00Z',
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-01T12:00:00Z',
});

describe('StaleDocsNotice', () => {
  beforeEach(() => window.localStorage.clear());

  it('points at the oldest stale reference page', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/nodes': {
        status: 200,
        body: { items: [doc('a', 'automation'), doc('b', 'events')] },
      },
    });
    renderWithProviders(<StaleDocsNotice space="eng" />);
    expect(await screen.findByText('2 reference pages went stale.')).toBeInTheDocument();
    expect(screen.getByText(/The oldest is “automation”/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Update it' })).toHaveAttribute(
      'href',
      '/folio/p/a-a/edit',
    );
    expect(screen.getByRole('link', { name: 'See the page' })).toHaveAttribute(
      'href',
      '/folio/p/a-a',
    );
    const url = decodeURIComponent(calls[0].path).replace(/\+/g, ' ');
    expect(url).toContain('status = outdated');
    expect(url).toContain('space = eng');
  });

  it('stays hidden once dismissed, until another page goes stale', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/nodes': { status: 200, body: { items: [doc('a', 'automation')] } },
    });
    const { unmount } = renderWithProviders(<StaleDocsNotice space="eng" />);
    await userEvent.click(await screen.findByRole('button', { name: 'Dismiss' }));
    expect(screen.queryByText('1 reference page went stale.')).toBeNull();
    unmount();
    renderWithProviders(<StaleDocsNotice space="eng" />);
    await waitFor(() => expect(calls).toHaveLength(2));
    expect(screen.queryByText('1 reference page went stale.')).toBeNull();
  });

  it('shows nothing when every page is current', async () => {
    const calls = mockFetch({ 'GET /api/v1/folio/nodes': { status: 200, body: { items: [] } } });
    const { container } = renderWithProviders(<StaleDocsNotice space="eng" />);
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(container.textContent).toBe('');
  });
});
