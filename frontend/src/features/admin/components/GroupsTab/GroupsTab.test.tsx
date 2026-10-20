import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { GroupsTab } from '.';

vi.mock('../../../../services/api/access', async (original) => ({
  ...(await original<typeof import('../../../../services/api/access')>()),
  fetchGroups: () =>
    Promise.resolve([{ name: 'legal-team', description: 'Lawyers', member_count: 2 }]),
  fetchGroup: () =>
    Promise.resolve({
      name: 'legal-team',
      description: 'Lawyers',
      members: [{ handle: 'vera', display_name: 'Vera', kind: 'human' }],
    }),
}));

describe('GroupsTab', () => {
  it('opens a group to show its members', async () => {
    renderWithProviders(<GroupsTab />);
    const toggle = await screen.findByRole('button', { name: /^legal-team/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(await screen.findByText('Vera')).toBeInTheDocument();
  });
});
