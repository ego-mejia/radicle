import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { AssistantSettings } from '.';

const base = { provider: 'none', model: '', base_url: '', has_key: false, managed_by_env: false };
const fetchSettings = vi.fn();
const save = vi.fn();
vi.mock('../../../../services/api/assistantAdmin', async (original) => ({
  ...(await original<typeof import('../../../../services/api/assistantAdmin')>()),
  fetchAssistantSettings: () => fetchSettings(),
  saveAssistantSettings: (body: unknown) => save(body),
  testAssistant: () => Promise.resolve({ ok: true, message: 'claude-haiku-5-5 answered: OK' }),
}));

describe('AssistantSettings', () => {
  it('connects Anthropic with a key and tests it', async () => {
    fetchSettings.mockResolvedValue(base);
    save.mockResolvedValue({ ...base, provider: 'anthropic', has_key: true });
    renderWithProviders(<AssistantSettings />);
    fireEvent.click(await screen.findByRole('radio', { name: /Anthropic/ }));
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        expect.objectContaining({ provider: 'anthropic', api_key: 'sk-1' }),
      ),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    expect(await screen.findByText('claude-haiku-5-5 answered: OK')).toBeInTheDocument();
  });

  it('is read-only when environment variables set it', async () => {
    fetchSettings.mockResolvedValue({ ...base, provider: 'anthropic', managed_by_env: true });
    renderWithProviders(<AssistantSettings />);
    expect(await screen.findByText(/environment variables/)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Anthropic/ })).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument();
  });
});
