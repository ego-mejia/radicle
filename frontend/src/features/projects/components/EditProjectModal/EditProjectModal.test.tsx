import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { EditProjectModal } from '.';

const patchProject = vi.fn().mockResolvedValue({});
vi.mock('../../../../services/api/projects', async (original) => ({
  ...(await original<typeof import('../../../../services/api/projects')>()),
  fetchProject: () => Promise.resolve({ key: 'PA', name: 'Acme', description_md: 'Shop' }),
  patchProject: (...args: unknown[]) => patchProject(...args),
}));

describe('EditProjectModal', () => {
  it('renames a project and keeps its key', async () => {
    const onClose = vi.fn();
    renderWithProviders(<EditProjectModal projectKey="PA" onClose={onClose} />);
    const name = await screen.findByLabelText('Name');
    expect(name).toHaveValue('Acme');
    expect(screen.getByLabelText(/^Key/)).toBeDisabled();
    fireEvent.change(name, { target: { value: 'Acme Store' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(patchProject).toHaveBeenCalledWith('PA', {
        name: 'Acme Store',
        description_md: 'Shop',
      }),
    );
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });
});
