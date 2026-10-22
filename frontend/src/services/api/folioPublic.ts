import { api, unwrap } from './client';
import type { components } from './schema';

export type PublicView = components['schemas']['PublicViewOut'];
export type PublicNode = components['schemas']['PublicNodeOut'];
export type PublicPage = components['schemas']['PublicPageOut'];
export type PrintView = components['schemas']['PrintOut'];
export type PublicLink = components['schemas']['PublicLinkOut'];

export const publicKeys = {
  view: (token: string, page: string | null) => ['folio', 'public', token, page] as const,
  links: (target: { node?: string; space?: string }) =>
    ['folio', 'public-links', target.node ?? null, target.space ?? null] as const,
};

/** What a public link shows: its page, or (for a space) one page of it or its index. */
export async function fetchPublic(token: string, page: string | null): Promise<PublicView> {
  if (page)
    return unwrap(
      await api.GET('/api/v1/folio/pub/{token}/pages/{node_id}', {
        params: { path: { token, node_id: page } },
      }),
    );
  return unwrap(await api.GET('/api/v1/folio/pub/{token}', { params: { path: { token } } }));
}

export function publicAssetUrl(token: string, assetId: string): string {
  return `/api/v1/folio/pub/${encodeURIComponent(token)}/assets/${assetId}`;
}

export async function fetchPublicLinks(target: {
  node?: string;
  space?: string;
}): Promise<PublicLink[]> {
  return unwrap(await api.GET('/api/v1/folio/public-links', { params: { query: target } })).items;
}

export async function createPublicLink(body: {
  node?: string;
  space?: string;
  noindex: boolean;
}): Promise<PublicLink> {
  return unwrap(await api.POST('/api/v1/folio/public-links', { body }));
}

export async function revokePublicLink(id: string): Promise<void> {
  unwrap(
    await api.DELETE('/api/v1/folio/public-links/{link_id}', {
      params: { path: { link_id: id } },
    }),
  );
}

/** The pages of an export being printed to PDF, by its short-lived token. */
export async function fetchPrint(token: string): Promise<PrintView> {
  return unwrap(await api.GET('/api/v1/folio/print/{token}', { params: { path: { token } } }));
}

export function printAssetUrl(token: string, assetId: string): string {
  return `/api/v1/folio/print/${encodeURIComponent(token)}/assets/${assetId}`;
}
