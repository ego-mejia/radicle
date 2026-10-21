import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DatabaseView } from '.';
import { DB_ID, dbApi } from './fixtures';

describe('DatabaseView', () => {
  it('shows the first view as a table, values by type', async () => {
    dbApi();
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

  it('switches views from the views bar', async () => {
    const calls = dbApi();
    renderWithProviders(<DatabaseView nodeId={DB_ID} />);
    await userEvent.click(await screen.findByRole('tab', { name: 'Cards' }));
    expect(await screen.findAllByRole('listitem')).toHaveLength(3);
    expect(screen.getByText('Seats')).toBeInTheDocument();
    expect(calls.some((c) => c.path.endsWith('/rows?view=cards'))).toBe(true);
  });

  it('inside a page shows one view and the database title, without the views bar', async () => {
    dbApi();
    renderWithProviders(<DatabaseView nodeId={DB_ID} viewId="cards" embedded />);
    expect(await screen.findByText('Inventario')).toBeInTheDocument();
    expect(await screen.findAllByRole('listitem')).toHaveLength(3);
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
  });

  it("says so when the reader can't see the database", async () => {
    mockFetch({});
    renderWithProviders(<DatabaseView nodeId={DB_ID} embedded />);
    expect(await screen.findByRole('note')).toHaveTextContent("You can't see this database.");
  });
});
