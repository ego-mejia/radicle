import { api, unwrap } from './client';
import type { FolioNode, FolioNodeRef, FolioSpace } from './folio';
import type { components } from './schema';

type S = components['schemas'];
export type FolioArchived = S['ArchivedOut'];
export type FolioCopyIn = S['CopyIn'];
export type FolioReaction = S['FolioReactionOut'];
export type FolioFavorites = S['FavoritesOut'];
export type FolioSpacePatch = S['SpacePatch'];
export type NodeStatus = FolioNode['status'];
export type Followable = 'node' | 'space';
export type Reactable = 'node' | 'comment';

/** Query keys for Folio's organization and social features (phase 2). */
export const socialKeys = {
  archived: (space: string) => ['folio', 'spaces', space, 'archived'] as const,
  watch: (type: Followable, id: string) => ['folio', 'watch', type, id] as const,
  reactions: (type: Reactable, id: string) => ['folio', 'reactions', type, id] as const,
  recents: ['folio', 'me', 'recents'] as const,
  favorites: ['folio', 'me', 'favorites'] as const,
};

const node = (id: string) => ({ params: { path: { node_id: id } } });

export async function archiveNode(id: string): Promise<FolioNode> {
  return unwrap(await api.POST('/api/v1/folio/nodes/{node_id}/archive', node(id)));
}

export async function unarchiveNode(id: string): Promise<FolioNode> {
  return unwrap(await api.POST('/api/v1/folio/nodes/{node_id}/unarchive', node(id)));
}

export async function fetchArchived(space: string): Promise<FolioArchived[]> {
  return unwrap(
    await api.GET('/api/v1/folio/spaces/{key}/archived', { params: { path: { key: space } } }),
  ).items;
}

export async function copyNode(id: string, body: FolioCopyIn): Promise<FolioNode> {
  return unwrap(await api.POST('/api/v1/folio/nodes/{node_id}/copy', { ...node(id), body }));
}

export async function setNodeStatus(
  id: string,
  status: 'published' | 'in_review' | 'verified',
): Promise<FolioNode> {
  return unwrap(
    await api.PATCH('/api/v1/folio/nodes/{node_id}/status', { ...node(id), body: { status } }),
  );
}

export async function transferOwner(id: string, owner: string): Promise<FolioNode> {
  return unwrap(
    await api.PATCH('/api/v1/folio/nodes/{node_id}/owner', { ...node(id), body: { owner } }),
  );
}

export async function patchSpace(key: string, body: FolioSpacePatch): Promise<FolioSpace> {
  return unwrap(await api.PATCH('/api/v1/folio/spaces/{key}', { params: { path: { key } }, body }));
}

const target = (type: string, id: string) => ({
  params: { path: { target_type: type as Followable, target_id: id } },
});

export async function fetchWatching(type: Followable, id: string): Promise<boolean> {
  return unwrap(await api.GET('/api/v1/folio/watch/{target_type}/{target_id}', target(type, id)))
    .watching;
}

export async function setWatching(type: Followable, id: string, on: boolean): Promise<void> {
  const path = '/api/v1/folio/watch/{target_type}/{target_id}' as const;
  unwrap(on ? await api.PUT(path, target(type, id)) : await api.DELETE(path, target(type, id)));
}

export async function setFavorite(type: Followable, id: string, on: boolean): Promise<void> {
  const path = '/api/v1/folio/favorites/{target_type}/{target_id}' as const;
  unwrap(on ? await api.PUT(path, target(type, id)) : await api.DELETE(path, target(type, id)));
}

export async function fetchFavorites(): Promise<FolioFavorites> {
  return unwrap(await api.GET('/api/v1/folio/me/favorites'));
}

export async function fetchRecents(): Promise<FolioNodeRef[]> {
  return unwrap(await api.GET('/api/v1/folio/me/recents')).items;
}

export async function fetchReactions(type: Reactable, id: string): Promise<FolioReaction[]> {
  return unwrap(
    await api.GET('/api/v1/folio/reactions/{target_type}/{target_id}', {
      params: { path: { target_type: type, target_id: id } },
    }),
  );
}

export async function setReaction(
  type: Reactable,
  id: string,
  emoji: string,
  on: boolean,
): Promise<FolioReaction[]> {
  const path = '/api/v1/folio/reactions/{target_type}/{target_id}/{emoji}' as const;
  const params = { params: { path: { target_type: type, target_id: id, emoji } } };
  return unwrap(on ? await api.PUT(path, params) : await api.DELETE(path, params));
}
