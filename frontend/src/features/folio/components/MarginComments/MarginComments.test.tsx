import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { MarginComments } from '.';

const thread = (id: string, extra: object) => ({
  id,
  kind: 'inline',
  anchor: { quote: `cita ${id}`, prefix: '', suffix: '', offset: 0 },
  orphaned: false,
  resolved_at: null,
  resolved_by: null,
  comments: [
    {
      id: `c-${id}`,
      thread_id: id,
      author: 'ana',
      author_name: 'Ana',
      body_md: `Comentario ${id}`,
      created_at: '2026-10-21T10:00:00Z',
      edited_at: null,
      mine: false,
    },
  ],
  ...extra,
});

describe('MarginComments', () => {
  it('shows only the open inline threads', async () => {
    mockFetch({
      'GET /api/v1/folio/nodes/n1/comments': {
        status: 200,
        body: {
          items: [
            thread('a', {}),
            thread('b', { orphaned: true }),
            thread('c', { resolved_at: '2026-10-21T11:00:00Z' }),
            thread('d', { kind: 'footer', anchor: null }),
          ],
        },
      },
      'GET /api/v1/folio/people': { status: 200, body: { items: [] } },
      'GET /api/v1/folio/reactions/comment/c-a': { status: 200, body: [] },
    });
    renderWithProviders(<MarginComments nodeId="n1" canComment={false} />);
    expect(await screen.findByText('Comentario a')).toBeInTheDocument();
    expect(screen.getByText('“cita a”')).toBeInTheDocument();
    for (const id of ['b', 'c', 'd']) expect(screen.queryByText(`Comentario ${id}`)).toBeNull();
  });
});
