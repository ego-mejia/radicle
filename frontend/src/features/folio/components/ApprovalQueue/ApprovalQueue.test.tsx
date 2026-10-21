import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { folioKeys } from '../../../../services/api/folio';
import { makeClient, mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { ApprovalQueue } from '.';

const submission = {
  id: 's1',
  node_id: 'n1',
  title: 'Cambios de la semana',
  status: 'pending',
  change_note: 'Desde el README',
  submitted_by: 'agente-docs',
  reviewed_by: null,
  review_comment: null,
  version: null,
  created_at: '2026-10-20T10:00:00Z',
  decided_at: null,
  metadata: {},
};
const detail = {
  ...submission,
  content_json: { type: 'doc', content: [] },
  content_md: '',
  current_version: null,
  changes: [],
  blocks: [],
};

function setup(role: 'admin' | 'creator') {
  const folio = { handle: 'luis', display_name: 'Luis', kind: 'human', role };
  const calls = mockFetch({
    'GET /api/v1/folio/me': { status: 200, body: folio },
    'GET /api/v1/folio/submissions': (request) => ({
      status: 200,
      body: {
        items: new URL(request.url).searchParams.get('status') === 'pending' ? [submission] : [],
      },
    }),
    'GET /api/v1/folio/submissions/s1': { status: 200, body: detail },
  });
  const client = makeClient();
  client.setQueryData(folioKeys.me, folio);
  renderWithProviders(<ApprovalQueue />, client);
  return calls;
}

describe('ApprovalQueue', () => {
  it('lists the pending queue and filters by status', async () => {
    const calls = setup('admin');
    const list = await screen.findByRole('list', { name: 'Submissions' });
    expect(within(list).getByText('Cambios de la semana')).toBeInTheDocument();
    expect(await screen.findByRole('region', { name: 'Cambios de la semana' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Rejected' }));
    expect(await screen.findByText('Nothing rejected.')).toBeInTheDocument();
    expect(calls.some((c) => c.path.endsWith('status=rejected'))).toBe(true);
  });

  it('shows others their own submissions without decisions', async () => {
    setup('creator');
    expect(await screen.findByText(/what you sent to publish/i)).toBeInTheDocument();
    await screen.findByRole('region', { name: 'Cambios de la semana' });
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
  });
});
