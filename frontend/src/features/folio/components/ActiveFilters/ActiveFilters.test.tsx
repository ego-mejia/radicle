import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { ActiveFilters } from '.';

describe('ActiveFilters', () => {
  it('removes one filter or clears them all', async () => {
    const remove = vi.fn();
    const clear = vi.fn();
    renderWithProviders(
      <ActiveFilters
        filters={[
          { key: 'project', label: 'RAD', onRemove: remove },
          { key: 'status', label: 'Done', onRemove: () => {} },
        ]}
        summary="3 specs"
        onClear={clear}
      />,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Remove RAD' }));
    expect(remove).toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'Clear' }));
    expect(clear).toHaveBeenCalled();
    expect(screen.getByText('3 specs')).toBeInTheDocument();
  });

  it('only shows the count with no filters on', async () => {
    renderWithProviders(<ActiveFilters filters={[]} summary="12 specs" />);
    expect(await screen.findByText('12 specs')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
