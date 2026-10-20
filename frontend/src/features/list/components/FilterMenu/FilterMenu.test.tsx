import { fireEvent, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { NO_FILTERS, type ListFilters } from '../../../../lib/listFilters';
import type { ProjectDetail } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { FilterMenu } from '.';

const project = {
  key: 'PA',
  members: [{ handle: 'ana', display_name: 'Ana' }],
  areas: [{ name: 'Backend', archived: false }],
  milestones: [{ name: 'V1' }],
} as unknown as ProjectDetail;

let last: ListFilters = NO_FILTERS;
function Harness() {
  const [value, setValue] = useState(NO_FILTERS);
  return (
    <FilterMenu
      project={project}
      value={value}
      onChange={(next) => {
        last = next;
        setValue(next);
      }}
    />
  );
}

describe('FilterMenu', () => {
  it('picks filters, shows them as chips and removes them', async () => {
    renderWithProviders(<Harness />);
    fireEvent.click(await screen.findByRole('button', { name: 'Filter' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Bug' }));
    fireEvent.click(screen.getByRole('button', { name: 'Unassigned' }));
    expect(last).toMatchObject({ type: ['bug'], assignee: ['@none'] });
    expect(screen.getByRole('button', { name: 'Remove Bug' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Remove Bug' }));
    expect(last.type).toEqual([]);
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
    expect(last).toEqual(NO_FILTERS);
  });
});
