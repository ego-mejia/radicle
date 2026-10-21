import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import { COLUMNS } from '../../../DatabaseView/fixtures';
import { FilterRow } from '.';

describe('FilterRow', () => {
  it('reads a number for a number column, and no value for "is empty"', async () => {
    const onChange = vi.fn();
    const { unmount } = renderWithProviders(
      <FilterRow
        columns={COLUMNS}
        filter={{ column: 'seats', op: 'gte', value: null }}
        onChange={onChange}
        onRemove={() => {}}
      />,
    );
    await userEvent.type(await screen.findByRole('spinbutton', { name: 'Value' }), '5');
    expect(onChange).toHaveBeenLastCalledWith({ column: 'seats', op: 'gte', value: 5 });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Operator' }), 'empty');
    expect(onChange).toHaveBeenLastCalledWith({ column: 'seats', op: 'empty', value: null });
    unmount();
    renderWithProviders(
      <FilterRow
        columns={COLUMNS}
        filter={{ column: 'seats', op: 'empty', value: null }}
        onChange={onChange}
        onRemove={() => {}}
      />,
    );
    expect(await screen.findByRole('combobox', { name: 'Operator' })).toHaveValue('empty');
    expect(screen.queryByRole('spinbutton', { name: 'Value' })).toBeNull();
  });

  it('a checkbox column filters by yes or no, and changing column clears the value', async () => {
    const onChange = vi.fn();
    const onRemove = vi.fn();
    renderWithProviders(
      <FilterRow
        columns={COLUMNS}
        filter={{ column: 'paid', op: 'eq', value: true }}
        onChange={onChange}
        onRemove={onRemove}
      />,
    );
    await userEvent.selectOptions(await screen.findByRole('combobox', { name: 'Value' }), 'false');
    expect(onChange).toHaveBeenLastCalledWith({ column: 'paid', op: 'eq', value: false });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Column' }), 'Name');
    expect(onChange).toHaveBeenLastCalledWith({ column: 'name', op: 'eq', value: null });
    await userEvent.click(screen.getByRole('button', { name: 'Remove' }));
    expect(onRemove).toHaveBeenCalled();
  });
});
