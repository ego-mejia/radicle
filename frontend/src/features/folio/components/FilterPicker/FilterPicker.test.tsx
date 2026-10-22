import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { FilterPicker, type FilterOption } from '.';

const features: FilterOption[] = [
  'Integraciones',
  'Búsqueda e IA',
  'Colaboración',
  'Editor',
  'Móvil',
  'Visuales',
  'Templates',
].map((label, i) => ({ value: label, label, count: 7 - i }));

function Multi({ initial = [] as string[] }) {
  const [selected, setSelected] = useState(initial);
  return (
    <FilterPicker
      label="Feature"
      options={features}
      selected={selected}
      onChange={setSelected}
      multi
      searchable
    />
  );
}

describe('FilterPicker', () => {
  it('shows chosen first, then the most used, and searches the rest', async () => {
    renderWithProviders(<Multi initial={['Templates']} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Feature: Templates' }));
    const items = screen.getAllByRole('menuitemcheckbox').map((b) => b.textContent);
    expect(items[0]).toContain('Templates');
    expect(items).toHaveLength(6);
    expect(screen.getByText('Search to see the 1 remaining')).toBeInTheDocument();
    await userEvent.type(screen.getByRole('searchbox'), 'visu');
    expect(screen.getByRole('menuitemcheckbox', { name: /Visuales/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('menuitemcheckbox', { name: /Visuales/ }));
    expect(screen.getByRole('button', { name: 'Feature: 2 chosen' })).toBeInTheDocument();
  });

  it('picks one value, or all, in single mode', async () => {
    const seen: string[][] = [];
    renderWithProviders(
      <FilterPicker
        label="Project"
        allLabel="All projects"
        options={[{ value: 'RAD', label: 'Folio', count: 6 }]}
        selected={['RAD']}
        onChange={(v) => seen.push(v)}
      />,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Project: Folio' }));
    await userEvent.click(screen.getByRole('menuitemradio', { name: 'All projects' }));
    expect(seen).toEqual([[]]);
  });

  it('shows a hint instead of options when it has nothing to offer yet', async () => {
    renderWithProviders(
      <FilterPicker
        label="Feature"
        options={[]}
        selected={[]}
        onChange={() => {}}
        hint="Pick a project first"
      />,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Feature: All' }));
    expect(screen.getByText('Pick a project first')).toBeInTheDocument();
  });
});
