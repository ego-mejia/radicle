import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { MappingDialog } from '.';

describe('MappingDialog', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('asks a target per removed status and sends mappings by type', async () => {
    const onConfirm = vi.fn();
    renderWithProviders(
      <MappingDialog
        removed={[
          {
            type: 'task',
            status: {
              ref: 'in_review',
              name: 'In Review',
              category: 'in_progress',
              is_initial: false,
            },
          },
        ]}
        targets={{
          task: [
            { ref: 'to_do', name: 'To Do', category: 'todo', is_initial: true },
            { ref: 'doing', name: 'Doing', category: 'in_progress', is_initial: false },
            { ref: 'done', name: 'Done', category: 'done', is_initial: false },
          ],
        }}
        onConfirm={onConfirm}
        onClose={() => undefined}
      />,
    );
    const select = await screen.findByRole('combobox', { name: 'In Review (Task) goes to' });
    expect(select).toHaveDisplayValue('Doing'); // same category by default
    await userEvent.selectOptions(select, 'done');
    await userEvent.click(screen.getByRole('button', { name: 'Save and move tickets' }));
    expect(onConfirm).toHaveBeenCalledWith({ task: { in_review: 'done' } });
  });
});
