import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { FolioTasksView } from '.';

const task = (id: string, text: string, bucket: string, due: string | null, done = false) => ({
  id,
  text,
  done,
  due,
  bucket,
  node: { id: 'n1', kind: 'page', title: 'Minuta', slug: 'minuta', icon: null },
  url: '/folio/p/n1-minuta',
  updated_at: '2026-10-21T10:00:00Z',
});

describe('FolioTasksView', () => {
  it('groups by when they are due and checks one off', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/me/tasks': {
        status: 200,
        body: {
          items: [
            task('t1', 'Mandar el contrato', 'overdue', '2026-10-19'),
            task('t2', 'Revisar el deploy', 'upcoming', '2026-10-25'),
            task('t3', 'Pensar en V2', 'no_date', null),
          ],
        },
      },
      'PATCH /api/v1/folio/action-items/t1': {
        status: 200,
        body: task('t1', 'Mandar el contrato', 'overdue', '2026-10-19', true),
      },
    });
    renderWithProviders(<FolioTasksView />);
    const overdue = await screen.findByRole('region', { name: /Overdue/ });
    expect(within(overdue).getByText('Mandar el contrato')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /Upcoming/ })).toHaveTextContent('Revisar el deploy');
    expect(screen.getByRole('region', { name: /No date/ })).toHaveTextContent('Pensar en V2');
    expect(screen.queryByRole('region', { name: /Today/ })).toBeNull();
    expect(within(overdue).getByRole('link', { name: 'Minuta' })).toHaveAttribute(
      'href',
      '/folio/p/n1-minuta',
    );
    fireEvent.click(screen.getByRole('checkbox', { name: 'Done: Mandar el contrato' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({ done: true }),
    );
  });

  it('says when there is nothing to do', async () => {
    mockFetch({ 'GET /api/v1/folio/me/tasks': { status: 200, body: { items: [] } } });
    renderWithProviders(<FolioTasksView />);
    expect(await screen.findByText('Nothing to do. Enjoy it.')).toBeInTheDocument();
  });
});
