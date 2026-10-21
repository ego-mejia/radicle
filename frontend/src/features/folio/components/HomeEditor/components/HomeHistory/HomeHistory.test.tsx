import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { HomeHistory } from '.';

function version(id: string, active: boolean) {
  return {
    id,
    layout: { columns: 12, blocks: [{ id: 'txt' }] },
    is_active: active,
    published_at: '2026-10-21T10:00:00Z',
    published_by: 'ana',
  };
}

describe('HomeHistory', () => {
  it('restores an earlier layout after confirming', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/admin/home/history': {
        status: 200,
        body: { items: [version('v2', true), version('v1', false)] },
      },
      'POST /api/v1/folio/admin/home/history/v1/restore': {
        status: 201,
        body: version('v3', true),
      },
    });
    const onRestored = vi.fn();
    renderWithProviders(<HomeHistory onRestored={onRestored} />);
    expect(await screen.findByText('Live')).toBeInTheDocument();
    expect(screen.getAllByText('@ana · 1 block')).toHaveLength(2);
    await userEvent.click(screen.getByRole('button', { name: 'Restore' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Restore' }));
    await vi.waitFor(() => expect(onRestored).toHaveBeenCalled());
    expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/v1/restore'))).toBe(true);
  });

  it('says when nothing was published', async () => {
    mockFetch({ 'GET /api/v1/folio/admin/home/history': { status: 200, body: { items: [] } } });
    renderWithProviders(<HomeHistory onRestored={vi.fn()} />);
    expect(
      await screen.findByText('Nothing published yet: readers see the default home.'),
    ).toBeInTheDocument();
  });
});
