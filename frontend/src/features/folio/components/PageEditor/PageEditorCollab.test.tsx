import { act, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Awareness } from 'y-protocols/awareness';
import * as Y from 'yjs';
import { ME, mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { PageEditor } from '.';

// A provider without a server: the room is this test.
type FakeProvider = {
  url: string;
  room: string;
  awareness: Awareness;
  emit: (event: string, value: unknown) => void;
};
const rooms = vi.hoisted(() => [] as FakeProvider[]);
vi.mock('y-websocket', async () => {
  const { Awareness: RoomAwareness } = await import('y-protocols/awareness');
  class Provider {
    awareness: Awareness;
    private handlers = new Map<string, ((value: never) => void)[]>();
    constructor(
      public url: string,
      public room: string,
      doc: Y.Doc,
    ) {
      this.awareness = new RoomAwareness(doc);
      rooms.push(this);
    }
    on(event: string, fn: (value: never) => void) {
      this.handlers.set(event, [...(this.handlers.get(event) ?? []), fn]);
    }
    off() {}
    emit(event: string, value: unknown) {
      for (const fn of this.handlers.get(event) ?? []) fn(value as never);
    }
    connect() {
      this.emit('status', { status: 'connected' });
      this.emit('sync', true);
    }
    destroy() {}
  }
  return { WebsocketProvider: Provider };
});

const NODE = {
  id: '9f3c0000-0000-4000-8000-000000000002',
  kind: 'live_doc',
  title: 'Daily',
  slug: 'daily',
  icon: null,
  space: 'docs',
  parent_id: null,
  cover_asset_id: null,
  published_at: null,
  created_at: '2026-10-20T10:00:00Z',
  updated_at: '2026-10-20T10:00:00Z',
  breadcrumbs: [],
  version: null,
  metadata: null,
  content_json: null,
  can_edit: true,
  can_delete: true,
};
const DRAFT = { content_json: { type: 'doc', content: [] }, content_md: '', metadata: {} };

describe('PageEditor, shared', () => {
  it('joins the room, shows who is in and never saves the draft itself', async () => {
    const calls = mockFetch({
      [`GET /api/v1/folio/nodes/${NODE.id}`]: { status: 200, body: NODE },
      [`GET /api/v1/folio/nodes/${NODE.id}/draft`]: { status: 200, body: DRAFT },
    });
    renderWithProviders(<PageEditor nodeId={NODE.id} collab />);
    await waitFor(() => expect(rooms.at(-1)?.room).toBe(NODE.id));
    const provider = rooms.at(-1)!;
    expect(provider.url).toMatch(/\/api\/v1\/folio\/collab$/);
    expect(provider.awareness.getLocalState()?.user).toMatchObject({ handle: ME.handle });
    await waitFor(() => expect(screen.getByText('Saved')).toBeInTheDocument());

    // Someone else and an agent join.
    const other = new Awareness(new Y.Doc());
    other.setLocalStateField('user', { name: 'Ana Torres', handle: 'ana', color: '#DB2777' });
    const agent = new Awareness(new Y.Doc());
    agent.setLocalStateField('user', {
      name: 'Agente',
      handle: 'agente',
      color: '#059669',
      agent: true,
    });
    act(() => {
      for (const peer of [other, agent]) {
        provider.awareness.states.set(peer.clientID, peer.getLocalState()!);
      }
      provider.awareness.emit('change', [{ added: [], updated: [], removed: [] }, 'test']);
    });
    expect(await screen.findByLabelText('2 people in this document')).toBeInTheDocument();
    expect(screen.getByText('Agente is writing')).toBeInTheDocument();

    act(() => provider.emit('status', { status: 'disconnected' }));
    expect(await screen.findByText('Offline: reconnecting')).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'PUT')).toBe(false);
  });
});
