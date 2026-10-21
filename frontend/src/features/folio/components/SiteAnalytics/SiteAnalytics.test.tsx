import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SiteAnalytics } from '.';

const SITE = {
  days: 30,
  views: 42,
  active_users: 7,
  daily: [{ day: '2026-10-21', views: 42, unique: 7 }],
  top_spaces: [{ key: 'docs', name: 'Ingeniería', views: 30, readers: 5 }],
  top_pages: [{ node_id: 'n1', title: 'Deploy', space: 'docs', views: 20, readers: 4 }],
  searches: 15,
  no_results: [
    { query: 'vpn', times: 3, last_at: '2026-10-21T10:00:00Z' },
    { query: 'onboarding', times: 1, last_at: '2026-10-20T10:00:00Z' },
  ],
  unanswered: [
    { question: '¿Cómo pido vacaciones?', feedback: null, asked_at: '2026-10-21T09:00:00Z' },
  ],
};

describe('SiteAnalytics', () => {
  it('shows activity, the most read and what people do not find', async () => {
    const calls = mockFetch({ 'GET /api/v1/folio/analytics/site': { status: 200, body: SITE } });
    renderWithProviders(<SiteAnalytics />);
    expect(await screen.findByRole('link', { name: 'Deploy' })).toBeInTheDocument();
    expect(screen.getByText('Searches without results').nextSibling).toHaveTextContent('4');
    expect(screen.getByText('vpn')).toBeInTheDocument();
    expect(screen.getByText(/3 times/)).toBeInTheDocument();
    expect(screen.getByText('¿Cómo pido vacaciones?')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ingeniería' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Last 90 days' }));
    await waitFor(() => expect(calls.at(-1)?.path).toContain('days=90'));
  });

  it('says when there is nothing yet, and shows errors', async () => {
    mockFetch({
      'GET /api/v1/folio/analytics/site': {
        status: 200,
        body: { ...SITE, top_pages: [], top_spaces: [], no_results: [], unanswered: [] },
      },
    });
    const { unmount } = renderWithProviders(<SiteAnalytics />);
    expect(await screen.findByText('Every search found something.')).toBeInTheDocument();
    unmount();
    mockFetch({
      'GET /api/v1/folio/analytics/site': {
        status: 403,
        body: { status: 403, detail: 'Folio admins only.', errors: [] },
      },
    });
    renderWithProviders(<SiteAnalytics />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Folio admins only.');
  });
});
