/** Grid order: top to bottom, then left to right. Phones stack the blocks in it. */
export function inGridOrder<T extends { x: number; y: number }>(blocks: T[]): T[] {
  return [...blocks].sort((a, b) => a.y - b.y || a.x - b.x);
}
