import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SpacePermissions } from '.';

const GRANTS = {
  grants: [
    { grantee_type: 'everyone', grantee: null, permissions: ['view'] },
    { grantee_type: 'user', grantee: 'fernando', permissions: ['admin'] },
  ],
};

describe('SpacePermissions', () => {
  it('adds a person, gives them create and saves every grant', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/spaces/eng/grants': { status: 200, body: GRANTS },
      'PUT /api/v1/folio/spaces/eng/grants': (_req, body) => ({ status: 200, body }),
    });
    renderWithProviders(<SpacePermissions space="eng" />);
    expect(await screen.findByLabelText('@fernando: Write')).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Handle or group'), '@luis');
    await userEvent.click(screen.getByRole('button', { name: 'Add' }));
    await userEvent.click(screen.getByLabelText('@luis: Write'));
    await userEvent.click(screen.getByRole('button', { name: 'Save permissions' }));
    const put = calls.find((c) => c.method === 'PUT');
    expect(put?.body).toEqual({
      grants: [
        ...GRANTS.grants,
        { grantee_type: 'user', grantee: 'luis', permissions: ['view', 'create'] },
      ],
    });
  });

  it('shows why saving failed', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces/eng/grants': { status: 200, body: GRANTS },
      'PUT /api/v1/folio/spaces/eng/grants': {
        status: 422,
        body: { status: 422, detail: "No user 'nadie'. Check the handle.", errors: [] },
      },
    });
    renderWithProviders(<SpacePermissions space="eng" />);
    await userEvent.click(await screen.findByRole('button', { name: 'Save permissions' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Check the handle');
  });
});
