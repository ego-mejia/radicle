import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { AiProviderSettings } from '.';

const base = {
  provider: 'none',
  chat_model: '',
  embedding_model: '',
  embedding_dimensions: null,
  base_url: '',
  has_key: false,
  features: {},
};
const fetchSettings = vi.fn();
const save = vi.fn();
const test = vi.fn();
vi.mock('../../../../services/api/ai', async (original) => ({
  ...(await original<typeof import('../../../../services/api/ai')>()),
  fetchAiSettings: () => fetchSettings(),
  saveAiSettings: (body: unknown) => save(body),
  testAi: () => test(),
}));

describe('AiProviderSettings', () => {
  it('saves OpenAI with an embedding model and tests the connection', async () => {
    fetchSettings.mockResolvedValue(base);
    save.mockResolvedValue({ ...base, provider: 'openai', has_key: true });
    test.mockResolvedValue({
      ok: true,
      message: 'text-embedding-3-small answered with 8 dimensions',
    });
    renderWithProviders(<AiProviderSettings />);
    fireEvent.click(await screen.findByRole('radio', { name: /^OpenAI Chat/ }));
    fireEvent.change(screen.getByLabelText('Embedding model'), {
      target: { value: 'text-embedding-3-small' },
    });
    fireEvent.change(screen.getByLabelText('Embedding dimensions'), { target: { value: '8' } });
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'sk-1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        expect.objectContaining({
          provider: 'openai',
          embedding_model: 'text-embedding-3-small',
          embedding_dimensions: 8,
          api_key: 'sk-1',
        }),
      ),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    expect(await screen.findByText(/answered with 8 dimensions/)).toBeInTheDocument();
  });

  it('shows why a test failed and can remove the saved key', async () => {
    fetchSettings.mockResolvedValue({ ...base, provider: 'anthropic', has_key: true });
    save.mockResolvedValue({ ...base, provider: 'anthropic' });
    test.mockResolvedValue({ ok: false, message: 'Anthropic has no embeddings API.' });
    renderWithProviders(<AiProviderSettings />);
    fireEvent.click(await screen.findByRole('button', { name: 'Test connection' }));
    expect(await screen.findByText('Anthropic has no embeddings API.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Remove key' }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(expect.objectContaining({ api_key: '' })),
    );
  });
});
