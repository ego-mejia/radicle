// Who else is in a document (Folio 2.2): the people and agents of a room, read from Yjs
// awareness. The palette matches the server's (folio/services/collab.py): eight colors
// that read on light and dark backgrounds.

export const PRESENCE_COLORS = [
  '#2563EB',
  '#DB2777',
  '#D97706',
  '#059669',
  '#7C3AED',
  '#DC2626',
  '#0891B2',
  '#65A30D',
] as const;

/** Pointers hide after this long without moving. */
export const POINTER_IDLE_MS = 10_000;
/** At most 30 pointer updates a second, as the server allows. */
export const POINTER_EVERY_MS = 34;

export type Pointer = { x: number; y: number; at: number };

export type Peer = {
  clientId: number;
  name: string;
  handle?: string;
  color: string;
  agent: boolean;
  pointer?: Pointer;
};

export function colorFor(key: string): string {
  let hash = 0;
  for (const ch of key) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return PRESENCE_COLORS[hash % PRESENCE_COLORS.length] ?? PRESENCE_COLORS[0];
}

type AwarenessLike = { getStates(): Map<number, Record<string, unknown>> };

/** Everyone in the room but this client, one entry per connection. */
export function readPeers(awareness: AwarenessLike, self: number): Peer[] {
  const peers: Peer[] = [];
  awareness.getStates().forEach((state, clientId) => {
    if (clientId === self) return;
    const user = state.user as Record<string, unknown> | undefined;
    if (!user || typeof user.name !== 'string') return;
    peers.push({
      clientId,
      name: user.name,
      handle: typeof user.handle === 'string' ? user.handle : undefined,
      color: typeof user.color === 'string' ? user.color : colorFor(user.name),
      agent: user.agent === true,
      pointer: state.pointer as Pointer | undefined,
    });
  });
  return peers.sort((a, b) => a.name.localeCompare(b.name));
}

/** People once each (several tabs count once), agents last. */
export function uniquePeople(peers: Peer[]): Peer[] {
  const seen = new Set<string>();
  const out: Peer[] = [];
  for (const peer of [...peers].sort((a, b) => Number(a.agent) - Number(b.agent))) {
    const key = peer.handle ?? peer.name;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(peer);
  }
  return out;
}

/** Calls `fn` at most once per `every` ms, keeping the last value. */
export function throttle<T>(fn: (value: T) => void, every: number): (value: T) => void {
  let last = 0;
  let pending: T | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  return (value: T) => {
    const now = Date.now();
    if (now - last >= every) {
      last = now;
      fn(value);
      return;
    }
    pending = value;
    if (timer) return;
    timer = setTimeout(
      () => {
        timer = undefined;
        last = Date.now();
        if (pending !== undefined) fn(pending);
        pending = undefined;
      },
      every - (now - last),
    );
  };
}
