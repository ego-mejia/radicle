import type { FolioThread } from '../../../../services/api/folioComments';

export type CommentFilter = 'open' | 'resolved' | 'orphaned';
export const FILTERS: CommentFilter[] = ['open', 'resolved', 'orphaned'];

/** Open threads still point at their text; orphaned ones lost it; resolved are done. */
export function inFilter(thread: FolioThread, filter: CommentFilter): boolean {
  const resolved = thread.resolved_at != null;
  if (filter === 'resolved') return resolved;
  if (filter === 'orphaned') return !resolved && thread.orphaned;
  return !resolved && !thread.orphaned;
}
