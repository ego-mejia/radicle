import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DatabaseView } from '.';
import { dropFor, groupsOf } from './components/BoardView/board';
import { COLUMNS, DATABASE, DB_ID, ROWS, dbApi } from './fixtures';

const status = COLUMNS[1]!;

describe('DatabaseView', () => {
  it('shows the first view as a table, values by type', async () => {
    dbApi({ ...DATABASE, can_edit: false });
    renderWithProviders(<DatabaseView nodeId={DB_ID} />);
    const table = await screen.findByRole('table');
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((h) => h.textContent),
    ).toEqual(['Name', 'Status', 'Owner', 'Seats', 'Paid']);
    expect(within(table).getByText('Claude')).toBeInTheDocument();
    expect(within(table).getByText('@vera')).toBeInTheDocument();
    expect(within(table).getByText('12')).toBeInTheDocument();
    expect(within(table).getByLabelText('Yes')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Table' })).toHaveAttribute('aria-selected', 'true');
  });

  it('switches to the board, grouped by its select column', async () => {
    const calls = dbApi();
    renderWithProviders(<DatabaseView nodeId={DB_ID} />);
    await userEvent.click(await screen.findByRole('tab', { name: 'Board' }));
    const board = await screen.findByLabelText('Board by Status');
    const groups = within(board).getAllByRole('heading');
    expect(groups.map((g) => g.textContent)).toEqual(['No value1', 'Idea1', 'Trial0', 'Adopted1']);
    expect(calls.some((c) => c.path.endsWith('/rows?view=board'))).toBe(true);
    expect(board.querySelectorAll('[aria-roledescription="draggable"]')).toHaveLength(3);
  });

  it('shows cards', async () => {
    dbApi();
    renderWithProviders(<DatabaseView nodeId={DB_ID} viewId="cards" />);
    expect(await screen.findAllByRole('listitem')).toHaveLength(3);
    expect(screen.getByText('Seats')).toBeInTheDocument();
  });

  it('inside a page shows one view and the database title, without the views bar', async () => {
    dbApi();
    renderWithProviders(<DatabaseView nodeId={DB_ID} viewId="board" embedded />);
    expect(await screen.findByText('Inventario')).toBeInTheDocument();
    expect(await screen.findByLabelText('Board by Status')).toBeInTheDocument();
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
  });

  it("says so when the reader can't see the database", async () => {
    mockFetch({});
    renderWithProviders(<DatabaseView nodeId={DB_ID} embedded />);
    expect(await screen.findByRole('note')).toHaveTextContent("You can't see this database.");
  });
});

describe('BoardView', () => {
  it('puts rows without a known choice in "No value", first', () => {
    const groups = groupsOf(status, ROWS);
    expect(groups.map((g) => [g.value, g.rows.map((r) => r.id)])).toEqual([
      ['__none__', ['r3']],
      ['Idea', ['r2']],
      ['Trial', []],
      ['Adopted', ['r1']],
    ]);
  });

  it('a drop on another group sets the value; on its own group nothing', () => {
    expect(dropFor(status, ROWS, 'r2', 'Trial')).toEqual({ row: ROWS[1], value: 'Trial' });
    expect(dropFor(status, ROWS, 'r1', '__none__')).toEqual({ row: ROWS[0], value: null });
    expect(dropFor(status, ROWS, 'r2', 'Idea')).toBeNull();
    expect(dropFor(status, ROWS, 'r3', '__none__')).toBeNull();
  });

  it('only editors get draggable cards', async () => {
    dbApi({ ...DATABASE, can_edit: false });
    renderWithProviders(<DatabaseView nodeId={DB_ID} viewId="board" />);
    const board = await screen.findByLabelText('Board by Status');
    await waitFor(() => expect(within(board).getByText('Claude')).toBeInTheDocument());
    expect(board.querySelector('[aria-roledescription="draggable"]')).toBeNull();
  });
});
