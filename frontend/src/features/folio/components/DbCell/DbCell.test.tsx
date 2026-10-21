import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { DbColumn } from '../../../../services/api/folioDatabases';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { COLUMNS } from '../DatabaseView/fixtures';
import { DbCell } from '.';
import { fromInput } from './value';

const col = (type: DbColumn['type'], name = 'X'): DbColumn => ({
  key: 'x',
  name,
  type,
  options: {
    choices: [
      { value: 'ai', color: 'blue' },
      { value: 'llm', color: 'red' },
    ],
  },
});

describe('DbCell', () => {
  it('edits text in place and saves on Enter', async () => {
    const onChange = vi.fn();
    renderWithProviders(<DbCell column={col('text', 'Name')} value="Claude" onChange={onChange} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Edit Name' }));
    const input = screen.getByRole('textbox', { name: 'Edit Name' });
    await userEvent.clear(input);
    await userEvent.type(input, 'Claude Code{Enter}');
    expect(onChange).toHaveBeenCalledWith('Claude Code');
  });

  it('Escape cancels, and an unchanged value saves nothing', async () => {
    const onChange = vi.fn();
    renderWithProviders(<DbCell column={col('text', 'Name')} value="Claude" onChange={onChange} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Edit Name' }));
    await userEvent.type(screen.getByRole('textbox'), ' x{Escape}');
    expect(screen.getByRole('button', { name: 'Edit Name' })).toHaveTextContent('Claude');
    await userEvent.click(screen.getByRole('button', { name: 'Edit Name' }));
    await userEvent.type(screen.getByRole('textbox'), '{Enter}');
    expect(onChange).not.toHaveBeenCalled();
  });

  it('a number saves as a number, and emptying it clears it', async () => {
    const onChange = vi.fn();
    renderWithProviders(<DbCell column={col('number', 'Seats')} value={12} onChange={onChange} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Edit Seats' }));
    const input = screen.getByRole('spinbutton', { name: 'Edit Seats' });
    await userEvent.clear(input);
    await userEvent.type(input, '30{Enter}');
    expect(onChange).toHaveBeenLastCalledWith(30);
    await userEvent.click(screen.getByRole('button', { name: 'Edit Seats' }));
    await userEvent.clear(screen.getByRole('spinbutton'));
    await userEvent.tab();
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it('a select saves on choosing, a checkbox on toggling', async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <>
        <DbCell column={COLUMNS[1]!} value="Idea" onChange={onChange} />
        <DbCell column={col('checkbox', 'Paid')} value={false} onChange={onChange} />
      </>,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Edit Status' }));
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Edit Status' }), 'Trial');
    expect(onChange).toHaveBeenLastCalledWith('Trial');
    await userEvent.click(screen.getByRole('checkbox', { name: 'Edit Paid' }));
    expect(onChange).toHaveBeenLastCalledWith(true);
  });

  it('a multi-select toggles each choice', async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <DbCell column={col('multi_select', 'Tags')} value={['ai']} onChange={onChange} />,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Edit Tags' }));
    await userEvent.click(screen.getByRole('checkbox', { name: 'llm' }));
    expect(onChange).toHaveBeenLastCalledWith(['ai', 'llm']);
    await userEvent.click(screen.getByRole('checkbox', { name: 'ai' }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it('without onChange only shows the value', async () => {
    renderWithProviders(<DbCell column={col('text', 'Name')} value="Claude" />);
    expect(await screen.findByText('Claude')).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });
});

describe('fromInput', () => {
  it('reads an input for its column', () => {
    expect(fromInput(col('number'), ' 7 ')).toBe(7);
    expect(fromInput(col('number'), 'siete')).toBe('siete');
    expect(fromInput(col('person'), '@Vera')).toBe('vera');
    expect(fromInput(col('text'), '   ')).toBeNull();
  });
});
