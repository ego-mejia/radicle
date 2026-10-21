import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { DatabaseView } from '.';
import { DATABASE, DB_ID, dbApi } from './fixtures';

const ROW = { id: 'r9', values: {}, updated_at: '2026-10-21T10:00:00Z' };

function editable() {
  return dbApi(DATABASE, {
    [`POST /api/v1/folio/databases/${DB_ID}/rows`]: { status: 201, body: ROW },
    'PATCH /api/v1/folio/rows/r2': (_r, body) => ({
      status: 200,
      body: { ...ROW, ...(body as object) },
    }),
    'PATCH /api/v1/folio/rows/r1': {
      status: 422,
      body: { status: 422, detail: "Seats takes a number; 'muchos' is not one.", errors: [] },
    },
    'DELETE /api/v1/folio/rows/r3': { status: 204, body: null },
  });
}

describe('editing a database', () => {
  it('changes a cell, adds a row and deletes one', async () => {
    const calls = editable();
    renderWithProviders(<DatabaseView nodeId={DB_ID} />);
    const table = await screen.findByRole('table');
    const devin = within(table).getByText('Devin').closest('tr')!;
    await userEvent.click(within(devin).getByRole('button', { name: 'Edit Status' }));
    await userEvent.selectOptions(within(devin).getByRole('combobox'), 'Trial');
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'PATCH')).toMatchObject({
        path: '/api/v1/folio/rows/r2',
        body: { values: { status: 'Trial' } },
      }),
    );

    await userEvent.click(screen.getByRole('button', { name: 'Add row' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ values: {} }),
    );

    const last = within(table).getByText('Sin estado').closest('tr')!;
    await userEvent.click(within(last).getByRole('button', { name: 'Delete row' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'DELETE' && c.path === '/api/v1/folio/rows/r3')).toBe(
        true,
      ),
    );
  });

  it('says why the server refused a value', async () => {
    editable();
    renderWithProviders(<DatabaseView nodeId={DB_ID} />);
    const table = await screen.findByRole('table');
    const claude = within(table).getByText('Claude').closest('tr')!;
    await userEvent.click(within(claude).getByRole('button', { name: 'Edit Seats' }));
    const input = within(claude).getByRole('spinbutton');
    await userEvent.clear(input);
    await userEvent.type(input, '5{Enter}');
    expect(
      await screen.findByText("Seats takes a number; 'muchos' is not one."),
    ).toBeInTheDocument();
  });

  it('readers and pages that embed it only see the rows', async () => {
    dbApi({ ...DATABASE, can_edit: false });
    const { unmount } = renderWithProviders(<DatabaseView nodeId={DB_ID} />);
    expect(await screen.findByText('Claude')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Add row' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Edit Name' })).toBeNull();
    unmount();

    dbApi();
    renderWithProviders(<DatabaseView nodeId={DB_ID} embedded />);
    expect(await screen.findByText('Claude')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete row' })).toBeNull();
  });
});
