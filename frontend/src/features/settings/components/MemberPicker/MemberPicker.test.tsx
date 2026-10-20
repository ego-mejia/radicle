import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { MemberPicker } from '.';

const putMember = vi.fn().mockResolvedValue({});
const putGroupRole = vi.fn().mockResolvedValue({});
vi.mock('../../../../services/api/projects', async (original) => ({
  ...(await original<typeof import('../../../../services/api/projects')>()),
  fetchMemberCandidates: () =>
    Promise.resolve({
      people: [{ handle: 'nora', display_name: 'Nora', kind: 'human' }],
      groups: [{ name: 'legal-team', description: 'Lawyers' }],
    }),
  putMember: (...args: unknown[]) => putMember(...args),
}));
vi.mock('../../../../services/api/access', async (original) => ({
  ...(await original<typeof import('../../../../services/api/access')>()),
  putGroupRole: (...args: unknown[]) => putGroupRole(...args),
}));

describe('MemberPicker', () => {
  it('adds a person or a group with the chosen role', async () => {
    renderWithProviders(<MemberPicker projectKey="PA" />);
    const search = await screen.findByRole('combobox', { name: 'Add people, agents or groups' });
    fireEvent.focus(search);
    fireEvent.click(await screen.findByRole('option', { name: /Nora/ }));
    fireEvent.change(screen.getByRole('combobox', { name: 'Role' }), {
      target: { value: 'admin' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    await waitFor(() => expect(putMember).toHaveBeenCalledWith('PA', 'nora', 'admin'));

    fireEvent.focus(search);
    fireEvent.click(await screen.findByRole('option', { name: /legal-team/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    await waitFor(() => expect(putGroupRole).toHaveBeenCalledWith('PA', 'legal-team', 'admin'));
  });
});
