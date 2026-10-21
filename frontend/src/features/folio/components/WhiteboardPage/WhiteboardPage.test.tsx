import { act, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Awareness } from 'y-protocols/awareness';
import * as Y from 'yjs';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { elementsOf } from '../../whiteboard/sync';
import { WhiteboardPage } from '.';

// Excalidraw draws on a canvas jsdom doesn't have: a stand-in records what it is given.
type Board = {
  props: Record<string, unknown> & { onChange?: (elements: unknown[]) => void };
  api: { updateScene: ReturnType<typeof vi.fn> };
};
const boards = vi.hoisted(() => [] as Board[]);
vi.mock('@excalidraw/excalidraw', async () => {
  const { useEffect } = await import('react');
  function Excalidraw(props: Board['props']) {
    useEffect(() => {
      const api = {
        updateScene: vi.fn(),
        getSceneElementsIncludingDeleted: () => [],
        getSceneElements: () => [],
        getAppState: () => ({}),
        getFiles: () => ({}),
      };
      boards.push({ props, api });
      (props.excalidrawAPI as (a: unknown) => void)(api);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps
    return <div data-testid="excalidraw" />;
  }
  return {
    Excalidraw,
    CaptureUpdateAction: { NEVER: 'NEVER' },
    exportToBlob: vi.fn(),
    exportToSvg: vi.fn(),
  };
});

// A provider without a server: the room is this test.
type FakeProvider = { room: string; doc: Y.Doc; awareness: Awareness };
const rooms = vi.hoisted(() => [] as FakeProvider[]);
vi.mock('y-websocket', async () => {
  const { Awareness: RoomAwareness } = await import('y-protocols/awareness');
  class Provider {
    awareness: Awareness;
    private handlers = new Map<string, ((value: never) => void)[]>();
    constructor(
      public url: string,
      public room: string,
      public doc: Y.Doc,
    ) {
      this.awareness = new RoomAwareness(doc);
      rooms.push(this);
    }
    on(event: string, fn: (value: never) => void) {
      this.handlers.set(event, [...(this.handlers.get(event) ?? []), fn]);
    }
    off() {}
    connect() {
      for (const fn of this.handlers.get('sync') ?? []) fn(true as never);
    }
    destroy() {}
  }
  return { WebsocketProvider: Provider };
});

const NODE = {
  id: '9f3c0000-0000-4000-8000-0000000000b1',
  kind: 'whiteboard',
  title: 'Arquitectura',
  slug: 'arquitectura',
  icon: null,
  space: 'docs',
  parent_id: null,
  cover_asset_id: null,
  published_at: null,
  created_at: '2026-10-21T10:00:00Z',
  updated_at: '2026-10-21T10:00:00Z',
  breadcrumbs: [],
  version: null,
  metadata: null,
  content_json: null,
  can_edit: false,
  can_delete: false,
};
const BOX = { id: 'box', type: 'rectangle', version: 1, versionNonce: 3, index: 'a0' };

describe('WhiteboardPage', () => {
  it('shows readers the saved scene, read only, with exports', async () => {
    mockFetch({
      [`GET /api/v1/folio/whiteboards/${NODE.id}`]: {
        status: 200,
        body: { ...NODE, node_id: NODE.id, elements: [BOX], updated_at: NODE.updated_at },
      },
    });
    renderWithProviders(<WhiteboardPage node={NODE as never} spaceName="Docs" />);
    expect(await screen.findByRole('heading', { name: 'Arquitectura' })).toBeInTheDocument();
    await screen.findByTestId('excalidraw');
    const board = boards.at(-1)!;
    expect(board.props.viewModeEnabled).toBe(true);
    expect(board.props.initialData).toMatchObject({ elements: [BOX] });
    await waitFor(() => expect(screen.getByRole('button', { name: 'PNG' })).toBeEnabled());
    expect(screen.getByRole('button', { name: 'SVG' })).toBeEnabled();
    expect(rooms).toHaveLength(0); // readers never join the room
  });

  it('lets editors draw together in the room', async () => {
    mockFetch({});
    renderWithProviders(
      <WhiteboardPage node={{ ...NODE, can_edit: true } as never} spaceName="Docs" />,
    );
    await screen.findByTestId('excalidraw');
    const room = rooms.at(-1)!;
    const board = boards.at(-1)!;
    expect(room.room).toBe(NODE.id);
    expect(board.props.viewModeEnabled).toBe(false);

    // What I draw goes into the shared scene...
    act(() => board.props.onChange?.([BOX]));
    expect(elementsOf(room.doc).get('box')).toEqual(BOX);

    // ...and what someone else draws comes onto my canvas.
    act(() => {
      room.doc.transact(() => {
        elementsOf(room.doc).set('note', { ...BOX, id: 'note', index: 'a1' });
      }, 'remote');
    });
    const scenes = board.api.updateScene.mock.calls
      .map(([scene]) => scene as { elements?: { id: string }[] })
      .filter((scene) => scene.elements);
    expect(scenes.at(-1)?.elements?.map((e) => e.id)).toEqual(['box', 'note']);
  });
});
