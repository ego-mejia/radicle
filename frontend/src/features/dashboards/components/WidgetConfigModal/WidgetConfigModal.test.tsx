import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { WidgetConfigModal } from '.';

describe('WidgetConfigModal', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('asks a count widget for RQL and a label', async () => {
    const onSave = vi.fn();
    renderWithProviders(<WidgetConfigModal type="count" onCancel={vi.fn()} onSave={onSave} />);
    await userEvent.type(await screen.findByLabelText('RQL'), 'type = bug');
    await userEvent.type(screen.getByLabelText('Label'), 'Bugs');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).toHaveBeenCalledWith('Count', { rql: 'type = bug', label: 'Bugs' });
  });

  it('defaults a distribution to bars by area and a milestone to the first project', async () => {
    const onSave = vi.fn();
    renderWithProviders(
      <WidgetConfigModal type="milestone_progress" onCancel={vi.fn()} onSave={onSave} />,
    );
    await userEvent.type(await screen.findByLabelText('Milestone'), 'V1');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).toHaveBeenCalledWith('Milestone progress', { milestone: 'V1', project: 'PA' });
  });
});
