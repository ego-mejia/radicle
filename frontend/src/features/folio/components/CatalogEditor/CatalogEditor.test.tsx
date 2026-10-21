import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { CatalogEditor } from '.';

const entry = (key: string, name: string, position: number, archived = false) => ({
  key,
  name,
  description: '',
  position,
  archived,
});
const API = '/api/v1/folio/admin/doc-types';

function setup() {
  const calls = mockFetch({
    [`GET ${API}`]: {
      status: 200,
      body: { items: [entry('how-to', 'How-to', 0), entry('guia', 'Guía', 1, true)] },
    },
    [`POST ${API}`]: (_r, body) => ({
      status: 201,
      body: { ...entry('', '', 2), ...(body as object) },
    }),
    [`PATCH ${API}/how-to`]: (_r, body) => ({
      status: 200,
      body: { ...entry('how-to', 'How-to', 0), ...(body as object) },
    }),
    [`PATCH ${API}/guia`]: (_r, body) => ({
      status: 200,
      body: { ...entry('guia', 'Guía', 1), ...(body as object) },
    }),
  });
  renderWithProviders(<CatalogEditor catalog="doc-types" />);
  return calls;
}

describe('CatalogEditor', () => {
  it('lists the entries and adds one', async () => {
    const calls = setup();
    expect(await screen.findByText('How-to')).toBeInTheDocument();
    expect(screen.getByText('Archived')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Key'), 'minuta');
    await userEvent.type(screen.getByLabelText('Name'), 'Minuta');
    await userEvent.click(screen.getByRole('button', { name: 'Add' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        key: 'minuta',
        name: 'Minuta',
      }),
    );
  });

  it('renames, archives and reorders', async () => {
    const calls = setup();
    await userEvent.click(await screen.findByRole('button', { name: 'Edit How-to' }));
    const name = screen.getByDisplayValue('How-to');
    await userEvent.clear(name);
    await userEvent.type(name, 'Cómo hacer');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({
        name: 'Cómo hacer',
        description: '',
      }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Restore Guía' }));
    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.path.endsWith('/guia') && (c.body as { archived?: boolean }).archived === false,
        ),
      ).toBe(true),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Move Guía up' }));
    await waitFor(() => {
      const moves = calls.filter((c) => (c.body as { position?: number })?.position !== undefined);
      expect(
        moves.map((c) => [c.path.split('/').pop(), (c.body as { position: number }).position]),
      ).toEqual([
        ['guia', 0],
        ['how-to', 1],
      ]);
    });
  });
});
