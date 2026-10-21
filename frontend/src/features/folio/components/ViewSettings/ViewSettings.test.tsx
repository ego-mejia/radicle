import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { DbView } from '../../../../services/api/folioDatabases';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { DATABASE, DB_ID, VIEWS, dbApi } from '../DatabaseView/fixtures';
import { ViewSettings } from '.';

function api() {
  return dbApi(DATABASE, {
    [`PATCH /api/v1/folio/databases/${DB_ID}`]: (_r, body) => {
      const views = (body as { views: DbView[] }).views.map((v) => ({
        ...v,
        id: v.id ?? 'view_4',
      }));
      return { status: 200, body: { ...DATABASE, views } };
    },
  });
}

const patched = (calls: ReturnType<typeof api>) =>
  calls.find((c) => c.method === 'PATCH')?.body as { views: DbView[] } | undefined;

describe('ViewSettings', () => {
  it('adds a filter and a sort to a view, keeping the other views', async () => {
    const calls = api();
    const onClose = vi.fn();
    renderWithProviders(<ViewSettings database={DATABASE} view={VIEWS[0]!} onClose={onClose} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Add filter' }));
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Column' }), 'Status');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Value' }), 'Adopted');
    await userEvent.click(screen.getByRole('button', { name: 'Add sort' }));
    const sortColumn = screen.getAllByRole('combobox', { name: 'Column' })[1]!;
    await userEvent.selectOptions(sortColumn, 'Seats');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Direction' }), 'desc');
    await userEvent.click(screen.getByRole('checkbox', { name: 'Owner' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(onClose).toHaveBeenCalledWith('table'));
    const views = patched(calls)!.views;
    expect(views.map((v) => v.id)).toEqual(['table', 'board', 'cards']);
    expect(views[0]).toMatchObject({
      filters: [{ column: 'status', op: 'eq', value: 'Adopted' }],
      sort: [{ column: 'seats', direction: 'desc' }],
      visible_columns: ['name', 'status', 'seats', 'paid'],
    });
  });

  it('makes a new board view and opens it', async () => {
    const calls = api();
    const onClose = vi.fn();
    renderWithProviders(<ViewSettings database={DATABASE} view={null} onClose={onClose} />);
    expect(await screen.findByRole('dialog', { name: 'New view' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Name' })).toHaveValue('View 4');
    await userEvent.selectOptions(screen.getByLabelText('Shown as'), 'board');
    expect(screen.getByLabelText('Group by')).toHaveValue('status');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(onClose).toHaveBeenCalledWith('view_4'));
    const views = patched(calls)!.views;
    expect(views).toHaveLength(4);
    expect(views[3]).toMatchObject({ name: 'View 4', kind: 'board', group_by: 'status' });
    expect(views[3]).not.toHaveProperty('id');
  });

  it('deletes a view and opens the first', async () => {
    const calls = api();
    const onClose = vi.fn();
    renderWithProviders(<ViewSettings database={DATABASE} view={VIEWS[1]!} onClose={onClose} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Delete view' }));
    await waitFor(() => expect(onClose).toHaveBeenCalledWith('table'));
    expect(patched(calls)!.views.map((v) => v.id)).toEqual(['table', 'cards']);
  });

  it('shows what the server refused', async () => {
    dbApi(DATABASE, {
      [`PATCH /api/v1/folio/databases/${DB_ID}`]: {
        status: 422,
        body: { status: 422, detail: 'Each view needs a name of 1 to 100 chars.', errors: [] },
      },
    });
    renderWithProviders(<ViewSettings database={DATABASE} view={VIEWS[0]!} onClose={() => {}} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Save' }));
    expect(
      await screen.findByText('Each view needs a name of 1 to 100 chars.'),
    ).toBeInTheDocument();
  });
});
