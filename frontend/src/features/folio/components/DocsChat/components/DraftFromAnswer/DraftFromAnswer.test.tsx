import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { ChatMessage } from '../../../../../../services/api/folioChat';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { ChatAnswer } from '../ChatAnswer';

const ANSWER: ChatMessage = {
  id: 'm1',
  role: 'assistant',
  content: 'Los eventos salen por el outbox [1].',
  citations: [
    {
      n: 1,
      node_id: '11111111-1111-1111-1111-111111111111',
      version: 2,
      anchor: 'decision',
      title: 'Eventos por el outbox',
      section: 'Decisión',
      url: '/folio/p/11111111-1111-1111-1111-111111111111-eventos#decision',
      outdated: false,
    },
  ],
  feedback: null,
  created_at: '2026-10-22T10:00:00Z',
};

const NODE = {
  id: '22222222-2222-2222-2222-222222222222',
  title: 'Qué decidimos sobre los eventos',
  slug: 'que-decidimos',
};

describe('Radi in Folio', () => {
  it('shows the tools it used and writes a draft with the answer and its sources', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/me/personal-space': { status: 200, body: { key: '~luis' } },
      'POST /api/v1/folio/nodes': { status: 201, body: NODE },
      [`PUT /api/v1/folio/nodes/${NODE.id}/draft`]: { status: 200, body: {} },
    });
    renderWithProviders(
      <ChatAnswer message={ANSWER} question="¿Qué decidimos sobre los eventos?" />,
    );
    expect(await screen.findByText(/search_docs · “¿Qué decidimos/)).toBeInTheDocument();
    expect(screen.getByText('get_page · Eventos por el outbox')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Write a draft with this' }));
    expect(await screen.findByRole('link', { name: 'Open the draft' })).toHaveAttribute(
      'href',
      `/folio/p/${NODE.id}-que-decidimos/edit`,
    );
    const create = calls.find((c) => c.method === 'POST');
    expect(create?.body).toEqual({
      space: '~luis',
      kind: 'page',
      title: 'Qué decidimos sobre los eventos',
    });
    const draft = calls.find((c) => c.method === 'PUT')?.body as { content_md: string };
    expect(draft.content_md).toContain('[Eventos por el outbox](/folio/p/');
  });

  it('shows neither tools nor drafts outside the Radi panel', async () => {
    renderWithProviders(<ChatAnswer message={ANSWER} />);
    await screen.findByText(/Los eventos salen/);
    expect(screen.queryByText(/search_docs/)).toBeNull();
    expect(screen.queryByRole('button', { name: 'Write a draft with this' })).toBeNull();
  });
});
