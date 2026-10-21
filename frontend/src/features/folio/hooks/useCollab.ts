import { useEffect, useState } from 'react';
import { WebsocketProvider } from 'y-websocket';
import * as Y from 'yjs';
import { readPeers, type Peer } from '../editor/presence';

export type CollabStatus = 'connecting' | 'connected' | 'disconnected';

export type Collab = {
  doc: Y.Doc;
  provider: WebsocketProvider;
  status: CollabStatus;
  synced: boolean;
  peers: Peer[];
};

export type Me = { name: string; handle: string; color: string };

/** The room's address: /api/v1/folio/collab/<node id> on this host. */
export function collabUrl(location: Location = window.location): string {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${scheme}://${location.host}/api/v1/folio/collab`;
}

/** Joins a document's room (Folio 2.2): the shared Y.Doc, the connection and who else is in. */
export function useCollab(nodeId: string, me: Me): Collab {
  const [{ doc, provider }] = useState(() => {
    const ydoc = new Y.Doc();
    return {
      doc: ydoc,
      provider: new WebsocketProvider(collabUrl(), nodeId, ydoc, { connect: false }),
    };
  });
  const [status, setStatus] = useState<CollabStatus>('connecting');
  const [synced, setSynced] = useState(false);
  const [peers, setPeers] = useState<Peer[]>([]);

  useEffect(() => {
    const { awareness } = provider;
    awareness.setLocalStateField('user', me);
    const onStatus = ({ status: next }: { status: CollabStatus }) => setStatus(next);
    const onSync = (value: boolean) => setSynced(value);
    const onChange = () => {
      const next = readPeers(awareness, doc.clientID);
      // Pointers move many times a second; skip renders when nothing changed.
      setPeers((now) => (JSON.stringify(now) === JSON.stringify(next) ? now : next));
    };
    provider.on('status', onStatus);
    provider.on('sync', onSync);
    awareness.on('change', onChange);
    provider.connect();
    return () => {
      awareness.off('change', onChange);
      provider.off('status', onStatus);
      provider.off('sync', onSync);
      provider.destroy();
      doc.destroy();
    };
    // One room for the life of the editor; `me` does not change while it is open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider, doc]);

  return { doc, provider, status, synced, peers };
}
