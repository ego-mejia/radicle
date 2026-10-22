import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type SpaceOverview = S['SpaceOverviewOut'];
export type SpaceSection = S['SpaceSectionOut'];
export type SpaceSectionKey = SpaceSection['key'];
export type SpaceParticipant = S['SpaceParticipantOut'];

/** Query keys for a space at a glance (RAD-57). */
export const spaceKeys = {
  overview: (key: string) => ['folio', 'spaces', key, 'overview'] as const,
  grants: (key: string) => ['folio', 'spaces', key, 'grants'] as const,
};

export async function fetchSpaceOverview(key: string): Promise<SpaceOverview> {
  return unwrap(
    await api.GET('/api/v1/folio/spaces/{key}/overview', { params: { path: { key } } }),
  );
}

export async function setSpaceSections(
  key: string,
  sections: { key: SpaceSectionKey; visible: boolean }[],
): Promise<SpaceSection[]> {
  return unwrap(
    await api.PUT('/api/v1/folio/spaces/{key}/sections', {
      params: { path: { key } },
      body: { sections },
    }),
  );
}

export type SpaceGrant = S['GrantIO'];
export type SpacePermission = SpaceGrant['permissions'][number];

export async function fetchSpaceGrants(key: string): Promise<SpaceGrant[]> {
  return unwrap(await api.GET('/api/v1/folio/spaces/{key}/grants', { params: { path: { key } } }))
    .grants;
}

export async function setSpaceGrants(key: string, grants: SpaceGrant[]): Promise<SpaceGrant[]> {
  return unwrap(
    await api.PUT('/api/v1/folio/spaces/{key}/grants', {
      params: { path: { key } },
      body: { grants },
    }),
  ).grants;
}
