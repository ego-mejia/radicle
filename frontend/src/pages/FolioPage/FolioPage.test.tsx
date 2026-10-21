import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { folioKeys } from '../../services/api/folio';
import { makeClient, mockFetch, renderWithProviders } from '../../test/renderWithProviders';
import { FolioPage } from '.';

function setup(role: 'admin' | 'creator') {
  const folio = { handle: 'luis', display_name: 'Luis', kind: 'human', role };
  mockFetch({
    'GET /api/v1/folio/me': { status: 200, body: folio },
    'GET /api/v1/folio/submissions': { status: 200, body: { items: [{ id: 's1' }] } },
  });
  const client = makeClient();
  client.setQueryData(folioKeys.me, folio);
  renderWithProviders(<FolioPage />, client);
}

describe('FolioPage', () => {
  it('shows admins the approvals link with the pending count', async () => {
    setup('admin');
    const link = await screen.findByRole('link', { name: /Approvals/ });
    expect(await screen.findByTitle('1 waiting for approval')).toHaveTextContent('1');
    expect(link).toHaveAttribute('href', '/folio/approvals');
  });

  it('has no approvals link for others', async () => {
    setup('creator');
    expect(await screen.findByRole('button', { name: 'Profile' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Approvals/ })).not.toBeInTheDocument();
  });
});
