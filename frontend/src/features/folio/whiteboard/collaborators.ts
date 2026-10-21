// The people in a whiteboard's room as Excalidraw draws collaborators (Folio 3.5).

import type { Collaborator, SocketId } from '@excalidraw/excalidraw/types';
import { POINTER_IDLE_MS, type Peer } from '../editor/presence';

/** Everyone else's pointers, as Excalidraw draws collaborators. */
export function collaborators(peers: Peer[], now = Date.now()): Map<SocketId, Collaborator> {
  const out = new Map<SocketId, Collaborator>();
  for (const peer of peers) {
    const live = peer.pointer && now - peer.pointer.at < POINTER_IDLE_MS;
    out.set(String(peer.clientId) as SocketId, {
      username: peer.name,
      color: { background: peer.color, stroke: peer.color },
      pointer: live ? { x: peer.pointer!.x, y: peer.pointer!.y, tool: 'pointer' } : undefined,
    });
  }
  return out;
}
