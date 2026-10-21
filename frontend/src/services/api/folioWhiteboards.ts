// Folio whiteboards (3.5): the scene as it is now. Drawing goes through the room.

import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type FolioWhiteboard = S['WhiteboardOut'];

export const whiteboardKeys = {
  whiteboard: (id: string) => ['folio', 'whiteboards', id] as const,
};

export async function fetchWhiteboard(id: string): Promise<FolioWhiteboard> {
  return unwrap(
    await api.GET('/api/v1/folio/whiteboards/{node_id}', { params: { path: { node_id: id } } }),
  );
}
