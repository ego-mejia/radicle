import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type FolioThread = S['FolioThreadOut'];
export type FolioComment = S['FolioCommentOut'];
export type FolioAnchor = S['FolioAnchor'];
export type FolioCommentIn = S['FolioCommentIn'];
export type FolioPerson = S['FolioPersonOut'];

/** Query keys for Folio's comments (phase 2.3). */
export const commentKeys = {
  threads: (nodeId: string, includeResolved: boolean) =>
    ['folio', 'nodes', nodeId, 'comments', includeResolved] as const,
  all: (nodeId: string) => ['folio', 'nodes', nodeId, 'comments'] as const,
  people: (q: string) => ['folio', 'people', q] as const,
};

const comment = (id: string) => ({ params: { path: { comment_id: id } } });

export async function fetchThreads(
  nodeId: string,
  includeResolved = false,
): Promise<FolioThread[]> {
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}/comments', {
      params: { path: { node_id: nodeId }, query: { include_resolved: includeResolved } },
    }),
  ).items;
}

/** A footer thread, an inline thread on `anchor`, or a reply to `thread_id`. */
export async function addComment(nodeId: string, body: FolioCommentIn): Promise<FolioThread> {
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/comments', {
      params: { path: { node_id: nodeId } },
      body,
    }),
  );
}

export async function editComment(id: string, body: string): Promise<FolioThread> {
  return unwrap(
    await api.PATCH('/api/v1/folio/comments/{comment_id}', { ...comment(id), body: { body } }),
  );
}

export async function deleteComment(id: string): Promise<void> {
  unwrap(await api.DELETE('/api/v1/folio/comments/{comment_id}', comment(id)));
}

export async function setResolved(id: string, resolved: boolean): Promise<FolioThread> {
  return unwrap(
    resolved
      ? await api.POST('/api/v1/folio/comments/{comment_id}/resolve', comment(id))
      : await api.POST('/api/v1/folio/comments/{comment_id}/reopen', comment(id)),
  );
}

/** People who read Folio, for @mentions. */
export async function fetchPeople(q = ''): Promise<FolioPerson[]> {
  return unwrap(await api.GET('/api/v1/folio/people', { params: { query: { q } } })).items;
}
