import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import type { WorkflowConf } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { WorkflowEditor } from '.';

vi.mock('mermaid', () => ({
  default: { initialize: vi.fn(), render: vi.fn(async () => ({ svg: '<svg></svg>' })) },
}));

const START: WorkflowConf = {
  statuses: [
    { ref: 'to_do', name: 'To Do', category: 'todo', is_initial: true },
    { ref: 'doing', name: 'Doing', category: 'in_progress', is_initial: false },
    { ref: 'done', name: 'Done', category: 'done', is_initial: false },
  ],
  transitions: [{ ref: 'start', name: 'Start', from: 'to_do', to: 'doing' }],
};

let latest: WorkflowConf = START;

function Harness() {
  const [value, setValue] = useState(START);
  latest = value;
  return <WorkflowEditor value={value} onChange={setValue} />;
}

describe('WorkflowEditor', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('adds a transition to done with limited resolutions', async () => {
    renderWithProviders(<Harness />);
    await userEvent.click(
      await screen.findByRole('button', { name: 'Add transition from Doing to Done' }),
    );
    const dialog = await screen.findByRole('dialog');
    const name = within(dialog).getByRole('textbox', { name: 'Transition name' });
    await userEvent.clear(name);
    await userEvent.type(name, 'Finish');
    await userEvent.click(within(dialog).getByRole('checkbox', { name: "Won't do" }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save' }));
    expect(latest.transitions?.at(-1)).toMatchObject({
      name: 'Finish',
      from: 'doing',
      to: 'done',
      allowed_resolutions: ['done', 'duplicate', 'cannot_reproduce'],
    });
    expect(screen.getByRole('button', { name: 'Finish' })).toBeInTheDocument();
  });

  it('removing a status drops its transitions and warns about errors', async () => {
    renderWithProviders(<Harness />);
    await userEvent.click(await screen.findByRole('button', { name: 'Remove Doing' }));
    expect(latest.statuses.map((s) => s.ref)).toEqual(['to_do', 'done']);
    expect(latest.transitions).toEqual([]);
    expect(screen.getByText('No transition reaches: Done.')).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole('radio', { name: 'Initial' })[1]!);
    expect(latest.statuses.filter((s) => s.is_initial).map((s) => s.ref)).toEqual(['done']);
  });
});
