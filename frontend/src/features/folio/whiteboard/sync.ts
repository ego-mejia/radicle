// A whiteboard's scene in Yjs (Folio 3.5): `Y.Map("elements")`, each Excalidraw element
// under its id, as the server reads it (folio/services/whiteboards.py). Both sides apply
// the same rule, so every client ends with the same scene: the higher version wins, and
// on a tie the lower versionNonce, as Excalidraw reconciles.

import * as Y from 'yjs';

export const ELEMENTS = 'elements';

export type SceneElement = {
  id: string;
  type: string;
  version: number;
  versionNonce?: number;
  isDeleted?: boolean;
  index?: string | null;
  [key: string]: unknown;
};

export function elementsOf(doc: Y.Doc): Y.Map<SceneElement> {
  return doc.getMap<SceneElement>(ELEMENTS);
}

/** Whether `incoming` should replace `current`. */
export function wins(incoming: SceneElement, current: SceneElement | undefined): boolean {
  if (!current) return true;
  if (incoming.version !== current.version) return incoming.version > current.version;
  return (incoming.versionNonce ?? 0) < (current.versionNonce ?? 0);
}

/** Write what changed on this screen into the shared map; returns how many were written. */
export function pushLocal(
  doc: Y.Doc,
  elements: readonly SceneElement[],
  origin: unknown = 'local',
): number {
  const map = elementsOf(doc);
  const changed = elements.filter((e) => wins(e, map.get(e.id)));
  if (changed.length)
    doc.transact(() => {
      // Excalidraw's elements are frozen objects; Yjs stores a plain copy.
      for (const e of changed) map.set(e.id, JSON.parse(JSON.stringify(e)) as SceneElement);
    }, origin);
  return changed.length;
}

function byIndex(a: SceneElement, b: SceneElement): number {
  const x = a.index ?? '';
  const y = b.index ?? '';
  // Fractional indices compare as plain strings, not by locale.
  if (x !== y) return x < y ? -1 : 1;
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

/** The scene to show: what is on screen, with the shared map's winners in, in order. */
export function merge(
  local: readonly SceneElement[],
  shared: Iterable<SceneElement>,
): SceneElement[] {
  const out = new Map<string, SceneElement>();
  for (const e of local) out.set(e.id, e);
  for (const e of shared) if (wins(e, out.get(e.id))) out.set(e.id, e);
  return [...out.values()].sort(byIndex);
}
