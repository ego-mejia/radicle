import type { FolioMoveIn, FolioTreeItem } from '../../../../services/api/folio';

/** Drop targets: the strip before a row, the row itself (becomes its child) or the root. */
export type DropTarget = `before:${string}` | `into:${string}` | 'root';

/** Each node's parent id (null at the root). */
export function parents(items: FolioTreeItem[], parent: string | null = null) {
  const out = new Map<string, string | null>();
  for (const item of items) {
    out.set(item.id, parent);
    for (const [id, p] of parents(item.children, item.id)) out.set(id, p);
  }
  return out;
}

function isInside(id: string, ancestor: string, parentOf: Map<string, string | null>): boolean {
  for (let at = parentOf.get(id) ?? null; at; at = parentOf.get(at) ?? null) {
    if (at === ancestor) return true;
  }
  return false;
}

/** The move for dropping `dragged` on `target`, or null when it would change nothing or
 * put a node inside itself. */
export function moveFor(
  dragged: string,
  target: DropTarget,
  items: FolioTreeItem[],
): FolioMoveIn | null {
  const parentOf = parents(items);
  if (target === 'root') return parentOf.get(dragged) === null ? null : { parent: null };
  const [kind, id] = target.split(':') as ['before' | 'into', string];
  if (id === dragged || isInside(id, dragged, parentOf)) return null;
  if (kind === 'into') return { parent: id };
  return { parent: parentOf.get(id) ?? null, before: id };
}
