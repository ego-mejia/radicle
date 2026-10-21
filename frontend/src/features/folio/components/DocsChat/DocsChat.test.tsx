import { fireEvent, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import type { ChatMessage } from '../../../../services/api/folioChat';
import { DocsChat } from '.';

const askDocs = vi.fn();
vi.mock('../../../../services/api/folioChat', () => ({
  chatKeys: { sessions: ['folio', 'chat', 'sessions'] },
  askDocs: (...args: unknown[]) => askDocs(...args),
  createChatSession: () => Promise.resolve({ id: 's1' }),
  sendChatFeedback: vi.fn(),
}));

const ANSWER: ChatMessage = {
  id: 'm1',
  role: 'assistant',
  content: 'Ve a Admin, Agentes.',
  citations: [],
  feedback: null,
  created_at: '2026-10-21T10:00:00Z',
};

beforeEach(() => {
  askDocs.mockReset();
});

async function ask(question: string) {
  const box = await screen.findByLabelText('Your question');
  fireEvent.change(box, { target: { value: question } });
  fireEvent.keyDown(box, { key: 'Enter' });
}

describe('DocsChat', () => {
  it('shows the answer as it is written, then the saved one', async () => {
    let finish: (m: ChatMessage) => void = () => {};
    askDocs.mockImplementation((_s, _q, onText: (p: string) => void) => {
      onText('Ve a ');
      return new Promise((resolve) => (finish = resolve));
    });
    renderWithProviders(<DocsChat space="docs" />);
    await ask('¿Cómo conecto un agente?');
    expect(await screen.findByText('Ve a')).toBeInTheDocument();
    expect(screen.getByText('¿Cómo conecto un agente?')).toBeInTheDocument();
    expect(askDocs).toHaveBeenCalledWith(
      's1',
      { content: '¿Cómo conecto un agente?', space: 'docs' },
      expect.any(Function),
    );
    finish(ANSWER);
    expect(await screen.findByRole('button', { name: 'Helpful' })).toBeInTheDocument();
    expect(screen.getByText('Ve a Admin, Agentes.')).toBeInTheDocument();
    expect(screen.queryByText('Ve a')).toBeNull();
  });

  it('keeps the session for the next question and shows errors', async () => {
    askDocs.mockResolvedValueOnce(ANSWER).mockRejectedValueOnce(new Error('boom'));
    renderWithProviders(<DocsChat />);
    await ask('Hola');
    await screen.findByText('Ve a Admin, Agentes.');
    await ask('¿Y luego?');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(askDocs.mock.calls.map((c) => c[0])).toEqual(['s1', 's1']);
  });
});
