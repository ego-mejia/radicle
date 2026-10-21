import { QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { makeClient, mockFetch } from '../../../test/renderWithProviders';
import { usePage } from './usePage';

const DOC = { type: 'doc', content: [] };
const NODE = { id: 'n1', space: 'docs', version: 1, content_json: DOC, metadata: { owner: 'ana' } };
const TREE = [
  {
    id: 'f1',
    title: 'Guías',
    children: [
      { id: 'n1', title: 'Deploy', children: [{ id: 'c1', title: 'Hija', children: [] }] },
    ],
  },
];

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={makeClient()}>{children}</QueryClientProvider>;
}

describe('usePage', () => {
  it('loads a published page with its space, author and child pages', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/nodes/n1': { status: 200, body: NODE },
      'GET /api/v1/folio/spaces/docs': {
        status: 200,
        body: { key: 'docs', permissions: ['view'] },
      },
      'GET /api/v1/folio/spaces/docs/tree': { status: 200, body: TREE },
      'GET /api/v1/folio/nodes/n1/versions': { status: 200, body: { items: [{ author: 'luis' }] } },
    });
    const { result } = renderHook(() => usePage('n1'), { wrapper });
    await waitFor(() => expect(result.current.children.map((c) => c.id)).toEqual(['c1']));
    await waitFor(() => expect(result.current.author).toBe('luis'));
    expect(result.current.isDraft).toBe(false);
    expect(result.current.canEdit).toBe(false);
    expect(result.current.content).toEqual(DOC);
    expect(result.current.metadata).toEqual({ owner: 'ana' });
    expect(calls.some((c) => c.path.endsWith('/draft'))).toBe(false);
  });

  it('reads the draft of a page that was never published', async () => {
    mockFetch({
      'GET /api/v1/folio/nodes/n1': {
        status: 200,
        body: { ...NODE, version: null, content_json: null, metadata: null, can_edit: true },
      },
      'GET /api/v1/folio/spaces/docs': {
        status: 200,
        body: { key: 'docs', permissions: ['create'] },
      },
      'GET /api/v1/folio/spaces/docs/tree': { status: 200, body: [] },
      'GET /api/v1/folio/nodes/n1/draft': {
        status: 200,
        body: { content_json: DOC, metadata: { doc_type: 'how-to' } },
      },
    });
    const { result } = renderHook(() => usePage('n1'), { wrapper });
    await waitFor(() => expect(result.current.content).toEqual(DOC));
    expect(result.current.isDraft).toBe(true);
    expect(result.current.metadata).toEqual({ doc_type: 'how-to' });
    await waitFor(() => expect(result.current.canEdit).toBe(true));
    expect(result.current.author).toBeNull();
  });
});
