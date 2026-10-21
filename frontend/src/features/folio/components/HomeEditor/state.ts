import type { HomeLayoutBlock } from '../../../../services/api/folio';

export const COLUMNS = 12;
export const MAX_HEIGHT = 12;

/** The block types the palette offers, in its order; chat waits for phase 4. */
export const PALETTE = [
  'featured',
  'announcement',
  'posts',
  'query',
  'for_you',
  'most_read',
  'spaces',
  'text',
  'search',
] as const;

const SIZES: Record<string, [number, number]> = {
  featured: [7, 4],
  announcement: [5, 2],
  posts: [4, 4],
  query: [4, 4],
  for_you: [4, 4],
  most_read: [6, 4],
  spaces: [3, 4],
  text: [6, 2],
  search: [12, 1],
  chat: [6, 4],
};

/** What react-grid-layout reports after a drag or resize. */
export type Placement = { i: string; x: number; y: number; w: number; h: number };

function freeId(blocks: HomeLayoutBlock[], type: string): string {
  const taken = new Set(blocks.map((b) => b.id));
  const base = type.replace(/_/g, '-');
  let n = 1;
  while (taken.has(n === 1 ? base : `${base}-${n}`)) n += 1;
  return n === 1 ? base : `${base}-${n}`;
}

/** A new block of `type`, full width under everything else. */
export function addBlock(blocks: HomeLayoutBlock[], type: string): HomeLayoutBlock[] {
  const [w, h] = SIZES[type] ?? [4, 2];
  const y = blocks.reduce((bottom, b) => Math.max(bottom, b.y + b.h), 0);
  return [...blocks, { id: freeId(blocks, type), type, x: 0, y, w, h, config: {} }];
}

/** The blocks where the grid left them; unchanged blocks keep their identity. */
export function applyPlacements(
  blocks: HomeLayoutBlock[],
  placements: Placement[],
): HomeLayoutBlock[] {
  const by = new Map(placements.map((p) => [p.i, p]));
  return blocks.map((b) => {
    const p = by.get(b.id);
    if (!p || (p.x === b.x && p.y === b.y && p.w === b.w && p.h === b.h)) return b;
    return { ...b, x: p.x, y: p.y, w: p.w, h: Math.min(p.h, MAX_HEIGHT) };
  });
}

export function removeBlock(blocks: HomeLayoutBlock[], id: string): HomeLayoutBlock[] {
  return blocks.filter((b) => b.id !== id);
}

export function setConfig(
  blocks: HomeLayoutBlock[],
  id: string,
  config: Record<string, unknown>,
): HomeLayoutBlock[] {
  return blocks.map((b) => (b.id === id ? { ...b, config: { ...b.config, ...config } } : b));
}

/** Whether the editor holds changes the saved draft doesn't have. */
export function isDirty(saved: HomeLayoutBlock[], current: HomeLayoutBlock[]): boolean {
  return JSON.stringify(saved) !== JSON.stringify(current);
}
