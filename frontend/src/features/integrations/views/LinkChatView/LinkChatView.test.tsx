import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { LinkChatView } from '.';

const link = vi.fn();
vi.mock('@tanstack/react-router', async (original) => ({
  ...(await original<typeof import('@tanstack/react-router')>()),
  useSearch: () => ({ token: 'tok' }),
}));
vi.mock('../../../../services/api/integrations', async (original) => ({
  ...(await original<typeof import('../../../../services/api/integrations')>()),
  linkChatAccount: (token: string) => link(token),
}));

describe('LinkChatView', () => {
  it('links the account behind the token', async () => {
    link.mockResolvedValue({ integration: 'Acme' });
    renderWithProviders(<LinkChatView />);
    fireEvent.click(await screen.findByRole('button', { name: 'Connect my account' }));
    await waitFor(() => expect(link).toHaveBeenCalledWith('tok'));
    expect(await screen.findByText(/Acme/)).toBeInTheDocument();
  });
});
