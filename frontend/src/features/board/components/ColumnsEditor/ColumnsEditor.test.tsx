import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import type { BoardStatus, ColumnConf } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { ColumnsEditor } from '.';

const statuses: BoardStatus[] = [
  { id: 's1', name: 'To Do', type: 'task', category: 'todo' },
  { id: 's2', name: 'In Review', type: 'task', category: 'in_progress' },
];

describe('ColumnsEditor', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('warns about unmapped statuses and maps one to a column', async () => {
    const onChange = vi.fn();
    const columns: ColumnConf[] = [
      { name: 'Backlog', status_ids: [], categories: ['todo'], wip_limit: null },
    ];
    renderWithProviders(
      <ColumnsEditor columns={columns} statuses={statuses} onChange={onChange} />,
    );
    expect(await screen.findByText(/in no column.*In Review/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('checkbox', { name: /In Review/ }));
    expect(onChange).toHaveBeenCalledWith([
      { name: 'Backlog', status_ids: ['s2'], categories: ['todo'], wip_limit: null },
    ]);
  });

  it('sets a WIP limit', async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <ColumnsEditor
        columns={[{ name: 'Doing', status_ids: ['s2'], categories: ['todo'], wip_limit: null }]}
        statuses={statuses}
        onChange={onChange}
      />,
    );
    await userEvent.type(await screen.findByRole('spinbutton', { name: 'WIP limit' }), '3');
    expect(onChange).toHaveBeenLastCalledWith([
      { name: 'Doing', status_ids: ['s2'], categories: ['todo'], wip_limit: 3 },
    ]);
  });
});
