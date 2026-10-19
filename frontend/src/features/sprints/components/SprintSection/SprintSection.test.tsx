import { DndContext } from '@dnd-kit/core';
import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import type { Sprint } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { SprintSection } from '.';

const sprint: Sprint = {
  id: 's1',
  board_id: 'b1',
  name: 'Sprint 4',
  goal: 'Pagos',
  state: 'future',
  start_date: null,
  end_date: null,
  capacity_hours: 10,
  started_at: null,
  completed_at: null,
  position: 0,
  goal_met: null,
  ticket_count: 3,
  done_count: 0,
  estimate_hours: 13,
  remaining_hours: 13,
  unestimated_count: 1,
  over_capacity: true,
};

describe('SprintSection', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('shows capacity over the limit and unestimated tickets', async () => {
    const onStart = vi.fn();
    renderWithProviders(
      <DndContext>
        <SprintSection
          sprint={sprint}
          tickets={[]}
          selected={new Set()}
          canEdit
          isAdmin
          canStart
          onSelect={vi.fn()}
          onOpen={vi.fn()}
          onStart={onStart}
        />
      </DndContext>,
    );
    const meter = await screen.findByRole('meter', { name: 'Capacity' });
    expect(meter).toHaveTextContent('13h of 10h');
    expect(meter).toHaveAttribute('aria-valuenow', '13');
    expect(screen.getByText('1 ticket without an estimate')).toBeInTheDocument();
    screen.getByRole('button', { name: 'Start sprint' }).click();
    expect(onStart).toHaveBeenCalled();
  });
});
