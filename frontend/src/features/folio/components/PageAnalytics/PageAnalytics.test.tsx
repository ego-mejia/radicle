import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { PageAnalytics } from '.';

const STATS = {
  days: 30,
  views: 12,
  unique_readers: 4,
  daily: [
    { day: '2026-10-20', views: 5, unique: 2 },
    { day: '2026-10-21', views: 7, unique: 3 },
  ],
  reading_minutes: 3,
  readers_visible: false,
  readers: [],
};

describe('PageAnalytics', () => {
  it('shows the numbers and keeps readers anonymous when the space only counts them', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/analytics/pages/n1': { status: 200, body: STATS },
    });
    renderWithProviders(<PageAnalytics nodeId="n1" open onOpenChange={() => {}} />);
    expect(await screen.findByText('12')).toBeInTheDocument();
    expect(screen.getByText('Unique readers').nextSibling).toHaveTextContent('4');
    expect(screen.getByText('3 min')).toBeInTheDocument();
    expect(screen.getByText(/only counts its readers/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Last 7 days' }));
    await waitFor(() => expect(calls.at(-1)?.path).toContain('days=7'));
  });

  it('names readers where the space allows it', async () => {
    mockFetch({
      'GET /api/v1/folio/analytics/pages/n1': {
        status: 200,
        body: {
          ...STATS,
          readers_visible: true,
          readers: [{ handle: 'ana', name: 'Ana Ruiz', views: 3, last_day: '2026-10-21' }],
        },
      },
    });
    renderWithProviders(<PageAnalytics nodeId="n1" open onOpenChange={() => {}} />);
    expect(await screen.findByText('@ana')).toBeInTheDocument();
    expect(screen.getByText(/3 views/)).toBeInTheDocument();
  });

  it('shows why it can’t', async () => {
    mockFetch({
      'GET /api/v1/folio/analytics/pages/n1': {
        status: 403,
        body: { status: 403, detail: "Only the owner of 'Deploy' can do that.", errors: [] },
      },
    });
    renderWithProviders(<PageAnalytics nodeId="n1" open onOpenChange={() => {}} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Only the owner');
  });
});
