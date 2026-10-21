import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { DbColumn, DbView } from '../../../../services/api/folioDatabases';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { DATABASE, DB_ID, dbApi } from '../DatabaseView/fixtures';
import { ColumnsDialog } from '.';
import { withKeys } from './keys';

type Body = { columns: DbColumn[]; views: DbView[] };

function api(cleared = 0) {
  return dbApi(DATABASE, {
    [`PATCH /api/v1/folio/databases/${DB_ID}`]: (_r, body) => ({
      status: 200,
      body: { ...DATABASE, ...(body as Body), cleared },
    }),
  });
}
const sent = (calls: ReturnType<typeof api>) =>
  calls.find((c) => c.method === 'PATCH')?.body as Body;

describe('ColumnsDialog', () => {
  it('adds a select column with choices, shown in every view', async () => {
    const calls = api();
    const onClose = vi.fn();
    renderWithProviders(<ColumnsDialog database={DATABASE} onClose={onClose} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Add column' }));
    const names = screen.getAllByRole('textbox', { name: 'Column name' });
    await userEvent.clear(names[5]!);
    await userEvent.type(names[5]!, 'Riesgo');
    await userEvent.selectOptions(screen.getAllByRole('combobox', { name: 'Type' })[5]!, 'select');
    const choices = screen.getAllByLabelText('Choices').at(-1)!;
    await userEvent.click(within(choices).getByRole('button', { name: 'Add choice' }));
    await userEvent.type(within(choices).getByRole('textbox', { name: 'Choice' }), 'Alto');
    await userEvent.selectOptions(within(choices).getByRole('combobox', { name: 'Color' }), 'red');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const body = sent(calls);
    expect(body.columns.at(-1)).toEqual({
      key: 'riesgo',
      name: 'Riesgo',
      type: 'select',
      options: { choices: [{ value: 'Alto', color: 'red' }] },
    });
    expect(body.views.every((v) => v.visible_columns.at(-1) === 'riesgo')).toBe(true);
  });

  it('renames, retypes and removes, and says how many values were cleared', async () => {
    const calls = api(2);
    renderWithProviders(<ColumnsDialog database={DATABASE} onClose={() => {}} />);
    const names = await screen.findAllByRole('textbox', { name: 'Column name' });
    await userEvent.type(names[3]!, ' (pagados)');
    await userEvent.selectOptions(screen.getAllByRole('combobox', { name: 'Type' })[3]!, 'text');
    expect(screen.getByRole('note')).toHaveTextContent("Values that don't fit");
    await userEvent.click(screen.getByRole('button', { name: 'Remove Owner' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(
      await screen.findByText("2 values didn't fit their column's new type and were cleared."),
    ).toBeInTheDocument();
    const body = sent(calls);
    expect(body.columns.map((c) => c.key)).toEqual(['name', 'status', 'seats', 'paid']);
    expect(body.columns[2]).toMatchObject({ name: 'Seats (pagados)', type: 'text' });
  });

  it('keeps the last column', async () => {
    api();
    renderWithProviders(
      <ColumnsDialog
        database={{ ...DATABASE, columns: [DATABASE.columns[0]!] }}
        onClose={() => {}}
      />,
    );
    expect(await screen.findByRole('button', { name: 'Remove Name' })).toBeDisabled();
  });
});

describe('withKeys', () => {
  it('names new columns from their name, never reusing a key', () => {
    const cols = withKeys([
      { key: 'status', name: 'Status', type: 'text', options: {} },
      { key: '', name: 'Status', type: 'text', options: {} },
      { key: '', name: 'Status', type: 'text', options: {} },
    ]);
    expect(cols.map((c) => c.key)).toEqual(['status', 'status_2', 'status_3']);
  });
});
