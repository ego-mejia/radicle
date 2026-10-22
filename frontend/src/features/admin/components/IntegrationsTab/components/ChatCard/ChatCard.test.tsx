import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import { ChatCard } from '.';

const api = {
  fetchChatIntegrations: vi.fn(),
  createChatIntegration: vi.fn(),
  deleteChatIntegration: vi.fn(),
  testChatIntegration: vi.fn(),
  fetchPublicEvents: vi.fn(),
};
vi.mock('../../../../../../services/api/integrations', async (original) => ({
  ...(await original<typeof import('../../../../../../services/api/integrations')>()),
  fetchChatIntegrations: () => api.fetchChatIntegrations(),
  createChatIntegration: (b: unknown) => api.createChatIntegration(b),
  deleteChatIntegration: (id: string) => api.deleteChatIntegration(id),
  testChatIntegration: (id: string, route: number) => api.testChatIntegration(id, route),
  fetchPublicEvents: () => api.fetchPublicEvents(),
}));

const slack = {
  id: 'i1',
  kind: 'slack',
  name: 'Acme',
  active: true,
  notices: [{ channel: 'C0ANUNCIOS', events: ['page.published'], filter: { space: 'anuncios' } }],
  command_url: 'https://radicle.acme.com/api/v1/hooks/chat/i1/command',
  events_url: 'https://radicle.acme.com/api/v1/hooks/chat/i1/events',
};

describe('ChatCard', () => {
  it('connects Slack with a channel for publications in a space', async () => {
    api.fetchChatIntegrations.mockResolvedValue([]);
    api.fetchPublicEvents.mockResolvedValue([{ name: 'page.published', label: 'Published' }]);
    api.createChatIntegration.mockResolvedValue(slack);
    renderWithProviders(<ChatCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'Connect Slack or Teams' }));
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Acme' } });
    fireEvent.change(screen.getByLabelText('Bot token'), { target: { value: 'xoxb-1' } });
    fireEvent.change(screen.getByLabelText('Signing secret'), { target: { value: 's' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add a channel' }));
    fireEvent.change(screen.getByLabelText('Channel 1'), { target: { value: 'C0ANUNCIOS' } });
    fireEvent.change(screen.getByLabelText('Only this space'), { target: { value: 'anuncios' } });
    fireEvent.click(await screen.findByRole('checkbox', { name: 'page.published' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(api.createChatIntegration).toHaveBeenCalledWith({
        kind: 'slack',
        name: 'Acme',
        credentials: { bot_token: 'xoxb-1', signing_secret: 's' },
        notices: [
          { channel: 'C0ANUNCIOS', events: ['page.published'], filter: { space: 'anuncios' } },
        ],
        active: true,
      }),
    );
  });

  it('asks Teams for its secret only', async () => {
    api.fetchChatIntegrations.mockResolvedValue([]);
    renderWithProviders(<ChatCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'Connect Slack or Teams' }));
    fireEvent.click(screen.getByRole('radio', { name: 'Teams' }));
    expect(screen.getByLabelText('Outgoing webhook secret')).toBeInTheDocument();
    expect(screen.queryByLabelText('Bot token')).not.toBeInTheDocument();
  });

  it('shows the URLs to paste and tests a channel', async () => {
    api.fetchChatIntegrations.mockResolvedValue([slack]);
    api.testChatIntegration.mockResolvedValue({
      ok: false,
      message: 'Slack answered channel_not_found.',
    });
    renderWithProviders(<ChatCard />);
    expect(await screen.findByText(slack.command_url)).toBeInTheDocument();
    expect(screen.getByText(slack.events_url)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Send a test to C0ANUNCIOS' }));
    await waitFor(() => expect(api.testChatIntegration).toHaveBeenCalledWith('i1', 0));
    expect(await screen.findByText('Slack answered channel_not_found.')).toBeInTheDocument();
  });
});
