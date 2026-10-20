import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import type { TourStep } from '../../lib/tour';
import { type ChatLine, RadiChat } from '.';

function Chat(props: {
  onClose?: () => void;
  onMood?: (m: string) => void;
  onTour?: (s: TourStep[]) => void;
}) {
  const [lines, setLines] = useState<ChatLine[]>([]);
  return (
    <RadiChat
      lines={lines}
      setLines={setLines}
      onClose={props.onClose ?? (() => {})}
      onMood={props.onMood ?? (() => {})}
      onTour={props.onTour ?? (() => {})}
    />
  );
}

const askRadi = vi.fn();
vi.mock('../../../../services/api/assistant', () => ({
  askRadi: (...args: unknown[]) => askRadi(...args),
}));

describe('RadiChat', () => {
  it('asks a suggested question, shows Radi thinking and his answer', async () => {
    let answer: (v: unknown) => void = () => {};
    askRadi.mockReturnValue(new Promise((resolve) => (answer = resolve)));
    const onMood = vi.fn();
    renderWithProviders(<Chat onMood={onMood} />);
    expect(await screen.findByText(/Hi! I'm Radi/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'How do I create a project?' }));
    expect(await screen.findByText('Radi is thinking…')).toBeInTheDocument();
    expect(onMood).toHaveBeenCalledWith('thinking');
    expect(askRadi).toHaveBeenCalledWith(
      [{ role: 'user', content: 'How do I create a project?' }],
      expect.any(String),
    );
    answer({
      answer: 'Go to **Projects**.',
      mode: 'guide',
      sources: [],
      notice: null,
      tour: [],
      autoplay: false,
    });
    expect(await screen.findByText('Projects')).toBeInTheDocument();
    await waitFor(() => expect(onMood).toHaveBeenCalledWith('answered'));
    // The menu comes back to ask something else.
    expect(screen.getByText('Ask something else:')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'How do I add people to a project?' })).toBeVisible();
  });

  it('sends with Enter and closes with Escape', async () => {
    askRadi.mockResolvedValue({
      answer: 'OK',
      mode: 'guide',
      sources: [],
      notice: 'AI is off',
      tour: [],
      autoplay: false,
    });
    const onClose = vi.fn();
    renderWithProviders(<Chat onClose={onClose} />);
    const box = await screen.findByRole('textbox', { name: 'Your question' });
    fireEvent.change(box, { target: { value: 'board columns' } });
    fireEvent.keyDown(box, { key: 'Enter' });
    expect(await screen.findByText('AI is off')).toBeInTheDocument();
    fireEvent.keyDown(box, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('offers Show me for guide tours and starts model tours at once', async () => {
    const tour = [{ target: 'projects.create', action: 'click', page: '/', text: 'Open it' }];
    askRadi.mockResolvedValueOnce({
      answer: 'Here',
      mode: 'guide',
      sources: [],
      notice: null,
      tour,
      autoplay: false,
    });
    const onTour = vi.fn();
    renderWithProviders(<Chat onTour={onTour} />);
    fireEvent.click(await screen.findByRole('button', { name: 'How do I create a project?' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Show me' }));
    expect(onTour).toHaveBeenCalledWith(tour);
    askRadi.mockResolvedValueOnce({
      answer: 'Follow me',
      mode: 'llm',
      sources: [],
      notice: null,
      tour,
      autoplay: true,
    });
    fireEvent.click(screen.getByRole('button', { name: 'How do I add people to a project?' }));
    await waitFor(() => expect(onTour).toHaveBeenCalledTimes(2));
  });
});
