import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import type { TransitionOption } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { TransitionPicker } from '.';

const BASE = { available: true, reasons: [], requires_comment: false, has_screen: false };
const OPTIONS: TransitionOption[] = [
  {
    ...BASE,
    name: 'Start',
    to_status: 'In Progress',
    category: 'in_progress',
    allowed_resolutions: null,
  },
  {
    ...BASE,
    name: 'Close',
    to_status: 'Done',
    category: 'done',
    allowed_resolutions: ['wont_do', 'duplicate'],
  },
  {
    ...BASE,
    name: 'Approve',
    to_status: 'Approved',
    category: 'done',
    allowed_resolutions: ['done'],
  },
];

describe('TransitionPicker', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('picks a plain transition directly', async () => {
    const onPick = vi.fn();
    renderWithProviders(<TransitionPicker options={OPTIONS} onPick={onPick} />);
    await userEvent.click(await screen.findByRole('menuitem', { name: /In Progress/ }));
    expect(onPick).toHaveBeenCalledWith({ option: OPTIONS[0], resolution: null });
  });

  it('asks for the resolution when several are allowed', async () => {
    const onPick = vi.fn();
    renderWithProviders(<TransitionPicker options={OPTIONS} onPick={onPick} />);
    await userEvent.click(await screen.findByRole('menuitem', { name: /Done/ }));
    expect(onPick).not.toHaveBeenCalled();
    expect(screen.getByText('Resolution for Done')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: 'Duplicate' }));
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Comment (optional)' }),
      'Dup of PA-2',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Move to Done' }));
    expect(onPick).toHaveBeenCalledWith({
      option: OPTIONS[1],
      resolution: 'duplicate',
      comment: 'Dup of PA-2',
      fields: null,
    });
  });

  it('applies a single allowed resolution automatically', async () => {
    const onPick = vi.fn();
    renderWithProviders(<TransitionPicker options={OPTIONS} onPick={onPick} />);
    await userEvent.click(await screen.findByRole('menuitem', { name: /Approved/ }));
    expect(onPick).toHaveBeenCalledWith({ option: OPTIONS[2], resolution: 'done' });
  });

  it('shows why a transition is unavailable and requires a comment when asked', async () => {
    const onPick = vi.fn();
    const options: TransitionOption[] = [
      {
        ...OPTIONS[0]!,
        available: false,
        reasons: [{ rule: 'only_assignee', message: 'Only the assignee can do this.' }],
      },
      {
        ...BASE,
        name: 'Stop',
        to_status: 'To Do',
        category: 'todo',
        allowed_resolutions: null,
        requires_comment: true,
      },
    ];
    renderWithProviders(<TransitionPicker options={options} onPick={onPick} />);
    const blocked = await screen.findByRole('menuitem', { name: /In Progress/ });
    expect(blocked).toBeDisabled();
    expect(blocked).toHaveTextContent('Only the assignee can do this.');
    await userEvent.click(screen.getByRole('menuitem', { name: /To Do/ }));
    const submit = screen.getByRole('button', { name: 'Move to To Do' });
    expect(submit).toBeDisabled();
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Comment (optional)' }),
      'Sin alcance',
    );
    await userEvent.click(submit);
    expect(onPick).toHaveBeenCalledWith({
      option: options[1],
      resolution: null,
      comment: 'Sin alcance',
      fields: null,
    });
  });

  it('says when there is nowhere to go', async () => {
    renderWithProviders(<TransitionPicker options={[]} onPick={() => undefined} />);
    expect(await screen.findByText('No transitions from here.')).toBeInTheDocument();
  });
});
