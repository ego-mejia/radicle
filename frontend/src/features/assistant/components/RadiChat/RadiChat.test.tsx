import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { RadiChat } from '.';

const askRadi = vi.fn();
vi.mock('../../../../services/api/assistant', () => ({
  askRadi: (...args: unknown[]) => askRadi(...args),
}));

describe('RadiChat', () => {
  it('asks a suggested question, shows Radi thinking and his answer', async () => {
    let answer: (v: unknown) => void = () => {};
    askRadi.mockReturnValue(new Promise((resolve) => (answer = resolve)));
    const onMood = vi.fn();
    renderWithProviders(<RadiChat onClose={() => {}} onMood={onMood} />);
    expect(await screen.findByText(/Hi! I'm Radi/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'How do I create a project?' }));
    expect(await screen.findByText('Radi is thinking…')).toBeInTheDocument();
    expect(onMood).toHaveBeenCalledWith('thinking');
    expect(askRadi).toHaveBeenCalledWith(
      [{ role: 'user', content: 'How do I create a project?' }],
      expect.any(String),
    );
    answer({ answer: 'Go to **Projects**.', mode: 'guide', sources: [], notice: null });
    expect(await screen.findByText('Projects')).toBeInTheDocument();
    await waitFor(() => expect(onMood).toHaveBeenCalledWith('answered'));
  });

  it('sends with Enter and closes with Escape', async () => {
    askRadi.mockResolvedValue({ answer: 'OK', mode: 'guide', sources: [], notice: 'AI is off' });
    const onClose = vi.fn();
    renderWithProviders(<RadiChat onClose={onClose} onMood={() => {}} />);
    const box = await screen.findByRole('textbox', { name: 'Your question' });
    fireEvent.change(box, { target: { value: 'board columns' } });
    fireEvent.keyDown(box, { key: 'Enter' });
    expect(await screen.findByText('AI is off')).toBeInTheDocument();
    fireEvent.keyDown(box, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
