import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { WriteButton } from '.';

const SPACES = {
  status: 200,
  body: {
    items: [
      { key: 'eng', name: 'Ingeniería', permissions: ['view', 'create'] },
      { key: 'hr', name: 'RRHH', permissions: ['view'] },
    ],
  },
};

describe('WriteButton', () => {
  it('starts a doc in a space you can write in', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/spaces': SPACES,
      'POST /api/v1/folio/nodes': { status: 201, body: { id: 'n9', slug: 'my-post' } },
    });
    renderWithProviders(<WriteButton />);
    await userEvent.click(await screen.findByRole('button', { name: 'Write' }));
    const space = await screen.findByRole('combobox', { name: 'Space' });
    await waitFor(() => expect(space).toHaveValue('eng'));
    expect(screen.queryByRole('option', { name: 'RRHH' })).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Type' }), 'page');
    await userEvent.type(screen.getByRole('textbox', { name: 'Title' }), 'My page');
    await userEvent.click(screen.getByRole('button', { name: 'Start writing' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        space: 'eng',
        kind: 'page',
        title: 'My page',
      }),
    );
    // It stays mounted in the shell's bar, so the dialog must close itself.
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('explains when no space lets you write', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces': { status: 200, body: { items: [SPACES.body.items[1]] } },
    });
    renderWithProviders(<WriteButton />);
    await userEvent.click(await screen.findByRole('button', { name: 'Write' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/create permission/);
    expect(screen.getByRole('button', { name: 'Start writing' })).toBeDisabled();
  });

  it('shows why the server refused', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces': SPACES,
      'POST /api/v1/folio/nodes': {
        status: 403,
        body: { status: 403, detail: 'You need the creator role.', errors: [] },
      },
    });
    renderWithProviders(<WriteButton />);
    await userEvent.click(await screen.findByRole('button', { name: 'Write' }));
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Space' })).toHaveValue('eng'));
    await userEvent.type(screen.getByRole('textbox', { name: 'Title' }), 'X');
    await userEvent.click(screen.getByRole('button', { name: 'Start writing' }));
    expect(await screen.findByText('You need the creator role.')).toBeInTheDocument();
  });
});
