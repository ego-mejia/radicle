import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import type { ChatMessage } from '../../../../../../services/api/folioChat';
import { linkCitations, pageOf } from '../../citations';
import { ChatAnswer } from '.';

const sendChatFeedback = vi.fn();
vi.mock('../../../../../../services/api/folioChat', () => ({
  sendChatFeedback: (...args: unknown[]) => sendChatFeedback(...args),
}));

const ANSWER: ChatMessage = {
  id: 'm1',
  role: 'assistant',
  content: 'Ve a Admin, Agentes [1].',
  citations: [
    {
      n: 1,
      node_id: 'n1',
      version: 2,
      anchor: 'conecta-un-agente',
      title: 'Conecta un agente',
      section: 'Conecta por MCP',
      url: '/folio/p/n1-conecta-un-agente#conecta-un-agente',
      outdated: true,
    },
  ],
  feedback: null,
  created_at: '2026-10-21T10:00:00Z',
};

describe('ChatAnswer', () => {
  it('links [n] and its sources to the section and warns about outdated docs', async () => {
    renderWithProviders(<ChatAnswer message={ANSWER} />);
    const source = await screen.findByRole('link', { name: /Conecta un agente/ });
    expect(source).toHaveAttribute('href', '/folio/p/n1-conecta-un-agente#conecta-un-agente');
    expect(screen.getByRole('link', { name: '[1]' })).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent('Outdated');
  });

  it('takes a thumbs down with a note', async () => {
    sendChatFeedback.mockResolvedValue({ ...ANSWER, feedback: 'down' });
    renderWithProviders(<ChatAnswer message={{ ...ANSWER, citations: [] }} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Not helpful' }));
    fireEvent.change(screen.getByLabelText('What was missing?'), {
      target: { value: 'Falta el token' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() =>
      expect(sendChatFeedback).toHaveBeenCalledWith('m1', 'down', 'Falta el token'),
    );
    expect(screen.queryByRole('note')).toBeNull();
  });

  it('links only the [n] it knows and finds the page param', () => {
    expect(linkCitations('Así [1] y [7].', ANSWER.citations)).toBe(
      'Así [\\[1\\]](/folio/p/n1-conecta-un-agente#conecta-un-agente) y [7].',
    );
    expect(pageOf('/folio/p/n1-conecta-un-agente#x')).toBe('n1-conecta-un-agente');
  });
});
