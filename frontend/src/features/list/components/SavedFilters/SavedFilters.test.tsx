import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { SavedFilters } from '.';

vi.mock('../../../../services/api/work', async (original) => ({
  ...(await original<typeof import('../../../../services/api/work')>()),
  fetchFilters: () =>
    Promise.resolve([
      { id: '1', name: 'My bugs', rql: 'type = bug', visibility: 'private', mine: true },
    ]),
}));

describe('SavedFilters', () => {
  it('opens as a dropdown and runs a filter', async () => {
    const onPick = vi.fn();
    renderWithProviders(<SavedFilters project="PA" query="" onPick={onPick} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Saved filters' }));
    fireEvent.click(await screen.findByRole('button', { name: 'My bugs' }));
    expect(onPick).toHaveBeenCalledWith('type = bug');
  });
});
