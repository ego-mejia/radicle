import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { makeClient, mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { folioKeys } from '../../../../services/api/folio';
import { FolioAdminView } from '.';

const admin = { handle: 'luis', display_name: 'Luis', kind: 'human', role: 'admin' };
const everyone = { id: 'g1', grantee_type: 'everyone', grantee: null, role: 'reader' };

describe('FolioAdminView', () => {
  it('lists the grants and gives a group a role', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/admin/grants': { status: 200, body: { items: [everyone] } },
      'POST /api/v1/folio/admin/grants': (_r, body) => ({
        status: 201,
        body: { id: 'g2', ...(body as object) },
      }),
    });
    const client = makeClient();
    client.setQueryData(folioKeys.me, admin);
    renderWithProviders(<FolioAdminView />, client);
    expect(await screen.findByText('Everyone')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Role of Everyone' })).toHaveValue('reader');
    await userEvent.type(screen.getByLabelText('Group'), 'equipo-docs');
    await userEvent.click(screen.getByRole('button', { name: 'Add' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        grantee_type: 'group',
        grantee: 'equipo-docs',
        role: 'creator',
      }),
    );
  });

  it('turns away readers and creators', async () => {
    mockFetch({});
    const client = makeClient();
    client.setQueryData(folioKeys.me, { ...admin, role: 'creator' });
    renderWithProviders(<FolioAdminView />, client);
    expect(await screen.findByText(/Only Folio admins/)).toBeInTheDocument();
  });
});
