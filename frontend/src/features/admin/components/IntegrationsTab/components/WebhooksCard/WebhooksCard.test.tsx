import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import { WebhooksCard } from '.';

const hook = {
  id: 'w1',
  name: 'CI',
  url: 'https://ci.example.com/radicle',
  events: ['page.published'],
  filter: {},
  active: true,
  created_at: '2026-10-21T10:00:00Z',
};
const api = {
  fetchWebhooks: vi.fn(),
  createWebhook: vi.fn(),
  deleteWebhook: vi.fn(),
  pingWebhook: vi.fn(),
  rotateWebhookSecret: vi.fn(),
  fetchDeliveries: vi.fn(),
  fetchPublicEvents: vi.fn(),
};
vi.mock('../../../../../../services/api/integrations', async (original) => ({
  ...(await original<typeof import('../../../../../../services/api/integrations')>()),
  fetchWebhooks: () => api.fetchWebhooks(),
  createWebhook: (b: unknown) => api.createWebhook(b),
  deleteWebhook: (id: string) => api.deleteWebhook(id),
  pingWebhook: (id: string) => api.pingWebhook(id),
  rotateWebhookSecret: (id: string) => api.rotateWebhookSecret(id),
  fetchDeliveries: (id: string) => api.fetchDeliveries(id),
  fetchPublicEvents: () => api.fetchPublicEvents(),
}));

describe('WebhooksCard', () => {
  it('creates a webhook for picked events and shows its secret once', async () => {
    api.fetchWebhooks.mockResolvedValue([]);
    api.fetchPublicEvents.mockResolvedValue([
      { name: 'page.published', label: 'A page is published' },
      { name: 'page.archived', label: 'A page is archived' },
    ]);
    api.createWebhook.mockResolvedValue({ ...hook, secret: 'whsec_abc' });
    renderWithProviders(<WebhooksCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'New webhook' }));
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'CI' } });
    fireEvent.change(screen.getByLabelText('Receiver URL'), { target: { value: hook.url } });
    fireEvent.change(screen.getByLabelText('Only this space'), { target: { value: 'eng' } });
    fireEvent.click(await screen.findByRole('checkbox', { name: 'page.published' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(api.createWebhook).toHaveBeenCalledWith({
        name: 'CI',
        url: hook.url,
        events: ['page.published'],
        filter: { space: 'eng' },
        active: true,
      }),
    );
    expect(await screen.findByText('whsec_abc')).toBeInTheDocument();
    expect(screen.getByText(/it isn't shown again/)).toBeInTheDocument();
  });

  it('pings a webhook and shows the delivery log with errors', async () => {
    api.fetchWebhooks.mockResolvedValue([hook]);
    api.pingWebhook.mockResolvedValue({});
    api.fetchDeliveries.mockResolvedValue([
      {
        id: 2,
        event: 'ping',
        status: 'failed',
        attempts: 6,
        response_status: 500,
        last_error: 'HTTP 500: boom',
        created_at: '2026-10-21T10:00:00Z',
        delivered_at: null,
      },
    ]);
    renderWithProviders(<WebhooksCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'Ping CI' }));
    await waitFor(() => expect(api.pingWebhook).toHaveBeenCalledWith('w1'));
    expect(await screen.findByText('HTTP 500: boom')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText(/6 attempts/)).toBeInTheDocument();
  });
});
