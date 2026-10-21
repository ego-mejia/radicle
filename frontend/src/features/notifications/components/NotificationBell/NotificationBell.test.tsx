import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { NotificationBell } from '.';

const PAGE = {
  unread: 1,
  next_cursor: null,
  items: [
    {
      id: 'n1',
      app: 'folio',
      type: 'comment_mention',
      title: 'Ana mentioned you',
      body: 'In "Deploy"',
      link: '/folio/p/x',
      actor_id: null,
      read: false,
      created_at: '2026-10-21T10:00:00Z',
    },
    {
      id: 'n2',
      app: 'folio',
      type: 'page_outdated',
      title: "'Deploy' is outdated",
      body: '',
      link: null,
      actor_id: null,
      read: true,
      created_at: '2026-10-20T10:00:00Z',
    },
  ],
};

describe('NotificationBell', () => {
  it('shows the unread count and lists the latest', async () => {
    mockFetch({ 'GET /api/v1/me/notifications': { status: 200, body: PAGE } });
    renderWithProviders(<NotificationBell />);
    const bell = await screen.findByRole('button', { name: 'Notifications, 1 unread' });
    expect(bell).toHaveTextContent('1');
    fireEvent.click(bell);
    expect(await screen.findByText('Ana mentioned you')).toBeInTheDocument();
    expect(screen.getByText("'Deploy' is outdated")).toBeInTheDocument();
    expect(screen.getAllByLabelText('Unread')).toHaveLength(1);
  });

  it('marks one read when opened, and all at once', async () => {
    const calls = mockFetch({
      'GET /api/v1/me/notifications': { status: 200, body: PAGE },
      'POST /api/v1/me/notifications/read': { status: 200, body: { marked: 1, unread: 0 } },
    });
    renderWithProviders(<NotificationBell />);
    fireEvent.click(await screen.findByRole('button', { name: /Notifications/ }));
    fireEvent.click(await screen.findByRole('button', { name: 'Mark all read' }));
    await waitFor(() => expect(calls.find((c) => c.method === 'POST')?.body).toEqual({}));
    fireEvent.click(await screen.findByText('Ana mentioned you')); // the panel stays open
    await waitFor(() =>
      expect(calls.filter((c) => c.method === 'POST').at(-1)?.body).toEqual({ ids: ['n1'] }),
    );
  });

  it('says when there is nothing', async () => {
    mockFetch({
      'GET /api/v1/me/notifications': {
        status: 200,
        body: { unread: 0, next_cursor: null, items: [] },
      },
    });
    renderWithProviders(<NotificationBell />);
    fireEvent.click(await screen.findByRole('button', { name: 'Notifications' }));
    expect(await screen.findByText('Nothing new.')).toBeInTheDocument();
  });
});
