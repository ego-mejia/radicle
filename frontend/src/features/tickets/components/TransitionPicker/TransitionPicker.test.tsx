import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import type { TransitionOption } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { TransitionPicker } from '.';

const OPTIONS: TransitionOption[] = [
  { name: 'Start', to_status: 'In Progress', category: 'in_progress', allowed_resolutions: null },
  {
    name: 'Close',
    to_status: 'Done',
    category: 'done',
    allowed_resolutions: ['wont_do', 'duplicate'],
  },
  { name: 'Approve', to_status: 'Approved', category: 'done', allowed_resolutions: ['done'] },
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
    await userEvent.click(screen.getByRole('button', { name: 'Duplicate' }));
    expect(onPick).toHaveBeenCalledWith({ option: OPTIONS[1], resolution: 'duplicate' });
  });

  it('applies a single allowed resolution automatically', async () => {
    const onPick = vi.fn();
    renderWithProviders(<TransitionPicker options={OPTIONS} onPick={onPick} />);
    await userEvent.click(await screen.findByRole('menuitem', { name: /Approved/ }));
    expect(onPick).toHaveBeenCalledWith({ option: OPTIONS[2], resolution: 'done' });
  });

  it('says when there is nowhere to go', async () => {
    renderWithProviders(<TransitionPicker options={[]} onPick={() => undefined} />);
    expect(await screen.findByText('No transitions from here.')).toBeInTheDocument();
  });
});
