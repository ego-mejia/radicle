import { api, isApiError, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type FolioMe = S['FolioMeOut'];
export type FolioGrant = S['GrantOut'];
export type FolioGrantIn = S['GrantIn'];

export const folioKeys = {
  me: ['folio', 'me'] as const,
  grants: ['folio', 'grants'] as const,
};

/** Your Folio role, or null when no grant reaches you (Folio is hidden then). */
export async function fetchFolioMe(): Promise<FolioMe | null> {
  try {
    return unwrap(await api.GET('/api/v1/folio/me'));
  } catch (error) {
    if (isApiError(error, 404)) return null;
    throw error;
  }
}

export async function fetchFolioGrants(): Promise<FolioGrant[]> {
  return unwrap(await api.GET('/api/v1/folio/admin/grants')).items;
}

export async function setFolioGrant(body: FolioGrantIn): Promise<FolioGrant> {
  return unwrap(await api.POST('/api/v1/folio/admin/grants', { body }));
}

export async function removeFolioGrant(id: string): Promise<void> {
  unwrap(
    await api.DELETE('/api/v1/folio/admin/grants/{grant_id}', {
      params: { path: { grant_id: id } },
    }),
  );
}
