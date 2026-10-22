import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import { RulesCard } from '.';

const api = {
  fetchRules: vi.fn(),
  createRule: vi.fn(),
  updateRule: vi.fn(),
  deleteRule: vi.fn(),
  fetchRuns: vi.fn(),
  fetchExamples: vi.fn(),
};
vi.mock('../../../../../../services/api/integrations', async (original) => ({
  ...(await original<typeof import('../../../../../../services/api/integrations')>()),
  fetchRules: () => api.fetchRules(),
  createRule: (b: unknown) => api.createRule(b),
  updateRule: (id: string, b: unknown) => api.updateRule(id, b),
  deleteRule: (id: string) => api.deleteRule(id),
  fetchRuns: (id: string) => api.fetchRuns(id),
  fetchExamples: () => api.fetchExamples(),
}));

const expiry = {
  name: 'Outdated pages to a channel',
  description: 'When a verified page expires, post it.',
  trigger: { type: 'event', event: 'page.outdated' },
  actions: [{ type: 'notify_channel', integration: '', route: 0 }],
};
const rule = {
  id: 'r1',
  name: 'Vencidos',
  trigger: expiry.trigger,
  filter: {},
  actions: expiry.actions,
  active: true,
  created_at: '2026-10-21T10:00:00Z',
  last_run_at: null,
};

describe('RulesCard', () => {
  beforeEach(() => vi.clearAllMocks());

  it('starts a rule from an example and saves it for a space', async () => {
    api.fetchRules.mockResolvedValue([]);
    api.fetchExamples.mockResolvedValue([expiry]);
    api.createRule.mockResolvedValue(rule);
    renderWithProviders(<RulesCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'New rule' }));
    await screen.findByRole('option', { name: expiry.name });
    fireEvent.change(screen.getByLabelText('Start from'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('Only this space'), { target: { value: 'docs' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(api.createRule).toHaveBeenCalledWith({
        name: expiry.name,
        trigger: expiry.trigger,
        actions: expiry.actions,
        filter: { space: 'docs' },
        active: true,
      }),
    );
  });

  it('says when the JSON is broken', async () => {
    api.fetchRules.mockResolvedValue([]);
    api.fetchExamples.mockResolvedValue([]);
    renderWithProviders(<RulesCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'New rule' }));
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'X' } });
    fireEvent.change(screen.getByLabelText('Actions'), { target: { value: '[{' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(
      await screen.findByText("The trigger or the actions aren't valid JSON."),
    ).toBeInTheDocument();
    expect(api.createRule).not.toHaveBeenCalled();
  });

  it('pauses a rule and reads its runs', async () => {
    api.fetchRules.mockResolvedValue([rule]);
    api.fetchExamples.mockResolvedValue([]);
    api.updateRule.mockResolvedValue({ ...rule, active: false });
    api.fetchRuns.mockResolvedValue([
      {
        id: 1,
        status: 'failed',
        target: '',
        log: ['notify_channel: The integration was removed.'],
        created_at: '2026-10-21T10:00:00Z',
      },
    ]);
    renderWithProviders(<RulesCard />);
    fireEvent.click(await screen.findByRole('button', { name: 'Pause Vencidos' }));
    await waitFor(() =>
      expect(api.updateRule).toHaveBeenCalledWith('r1', expect.objectContaining({ active: false })),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Runs of Vencidos' }));
    expect(
      await screen.findByText('notify_channel: The integration was removed.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });
});
