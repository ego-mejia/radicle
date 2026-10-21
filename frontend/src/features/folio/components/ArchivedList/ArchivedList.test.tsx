import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { ArchivedList } from '.';

const ARCHIVED = {
  items: [
    {
      id: 'n1',
      kind: 'page',
      title: 'Guía vieja',
      slug: 'guia-vieja',
      icon: null,
      status: 'published',
      archived_at: '2026-10-21T10:00:00Z',
      archived_by: 'ana',
    },
  ],
};

describe('ArchivedList', () => {
  it('lists what was archived and restores it', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/spaces/docs/archived': { status: 200, body: ARCHIVED },
      'POST /api/v1/folio/nodes/n1/unarchive': {
        status: 200,
        body: { id: 'n1', title: 'Guía vieja' },
      },
    });
    renderWithProviders(<ArchivedList space="docs" canRestore />);
    await userEvent.click(await screen.findByRole('button', { name: 'Archived (1)' }));
    expect(screen.getByText(/By @ana/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Restore Guía vieja' }));
    expect(await screen.findByText('“Guía vieja” is back')).toBeInTheDocument();
    expect(calls.some((c) => c.path.endsWith('/unarchive'))).toBe(true);
  });

  it('shows nothing when nothing is archived', async () => {
    mockFetch({ 'GET /api/v1/folio/spaces/docs/archived': { status: 200, body: { items: [] } } });
    renderWithProviders(<ArchivedList space="docs" canRestore />);
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByRole('button', { name: /Archived/ })).toBeNull();
  });
});
